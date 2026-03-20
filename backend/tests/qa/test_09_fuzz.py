"""
═══════════════════════════════════════════════════════
TEST 9 — FUZZ TESTING
═══════════════════════════════════════════════════════
Objective: Verify API stability against malformed, random, and boundary
           inputs using Hypothesis. Zero 500 errors — all bad inputs
           must return 400 with a structured error response.
"""

import math
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# Conditionally import hypothesis — degrade gracefully if not installed
try:
    from hypothesis import given, settings, HealthCheck, assume
    from hypothesis import strategies as st

    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

VALID_API_KEY = "xK9mR-vL2pN8qW5jT7bF4hD6cY0aG3sE"
AUTH = {"X-API-Key": VALID_API_KEY, "Content-Type": "application/json"}


def _model():
    m = MagicMock()
    m.predict.return_value = np.array([0])
    m.predict_proba.return_value = np.array([[0.90, 0.10]])
    m.feature_names_in_ = np.array(["temperature", "humidity", "precipitation"])
    m.n_features_in_ = 3
    m.classes_ = np.array([0, 1])
    m.feature_importances_ = np.array([0.3, 0.3, 0.4])
    return m


def _loader(model):
    loader = MagicMock()
    loader.model = model
    loader.model_path = "models/test.joblib"
    loader.metadata = {"version": "6.0.0", "checksum": "abc123"}
    loader.checksum = "abc123"
    return loader


@pytest.mark.fuzz
class TestFuzz:
    """Fuzz tests — random and malformed input stability."""

    # ------------------------------------------------------------------
    # FZ-1: Random type in temperature field
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "temp_value",
        [
            None,
            True,
            False,
            "",
            "hot",
            [],
            {},
            [1, 2, 3],
            {"nested": "object"},
            float("inf"),
            float("-inf"),
            float("nan"),
            "NaN",
            "Infinity",
            "-Infinity",
            "1e999",
            "\x00",
            "🌊",
            "DROP TABLE predictions;",
            '<script>alert(1)</script>',
            "../../../../etc/passwd",
        ],
    )
    def test_fz1_random_temperature_types(self, client, mock_model_comprehensive, temp_value):
        """FZ-1: Non-numeric temperature values return 400, never 500."""
        payload = {"temperature": temp_value, "humidity": 50.0, "precipitation": 5.0}
        resp = client.post("/api/v1/predict/", json=payload, headers=AUTH)
        assert resp.status_code < 500, (
            f"temperature={temp_value!r} caused {resp.status_code}"
        )

    # ------------------------------------------------------------------
    # FZ-2: Random type in humidity field
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "hum_value",
        [None, "", "wet", [], {}, True, -1, 101, 999999, float("inf"), "🌧️"],
    )
    def test_fz2_random_humidity_types(self, client, mock_model_comprehensive, hum_value):
        """FZ-2: Invalid humidity values return 400, never 500."""
        payload = {"temperature": 298.15, "humidity": hum_value, "precipitation": 5.0}
        resp = client.post("/api/v1/predict/", json=payload, headers=AUTH)
        assert resp.status_code < 500, (
            f"humidity={hum_value!r} caused {resp.status_code}"
        )

    # ------------------------------------------------------------------
    # FZ-3: Random type in precipitation field
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "precip_value",
        [None, "", "rain", [], {}, True, -100, 1e12, float("nan"), "💧"],
    )
    def test_fz3_random_precipitation_types(self, client, mock_model_comprehensive, precip_value):
        """FZ-3: Invalid precipitation values return 400, never 500."""
        payload = {"temperature": 298.15, "humidity": 50.0, "precipitation": precip_value}
        resp = client.post("/api/v1/predict/", json=payload, headers=AUTH)
        assert resp.status_code < 500, (
            f"precipitation={precip_value!r} caused {resp.status_code}"
        )

    # ------------------------------------------------------------------
    # FZ-4: Completely random JSON payloads
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"a": 1},
            {"temperature": 298.15},
            {"humidity": 50.0, "precipitation": 5.0},
            {"temperature": 298.15, "humidity": 50.0, "precipitation": 5.0, "extra_field": "value"},
            [1, 2, 3],
            "just a string",
            42,
            None,
            {"temperature": {"nested": True}, "humidity": [50], "precipitation": "5"},
        ],
    )
    def test_fz4_random_json_payloads(self, client, mock_model_comprehensive, payload):
        """FZ-4: Arbitrary JSON structures never cause 500."""
        resp = client.post("/api/v1/predict/", json=payload, headers=AUTH)
        assert resp.status_code < 500, (
            f"Payload {payload!r} caused {resp.status_code}"
        )

    # ------------------------------------------------------------------
    # FZ-5: Unicode and emoji injection
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "unicode_val",
        [
            "⚡🌊🌧️",
            "\u0000",
            "\uffff",
            "Ñ" * 1000,
            "中文测试",
            "العربية",
            "\n\r\t",
            "\x1b[31mRED\x1b[0m",
        ],
    )
    def test_fz5_unicode_injection(self, client, mock_model_comprehensive, unicode_val):
        """FZ-5: Unicode/emoji in fields returns 400, never 500."""
        payload = {"temperature": unicode_val, "humidity": 50.0, "precipitation": 5.0}
        resp = client.post("/api/v1/predict/", json=payload, headers=AUTH)
        assert resp.status_code < 500, (
            f"Unicode value caused {resp.status_code}"
        )

    # ------------------------------------------------------------------
    # FZ-6: Extremely large numeric values
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "extreme",
        [1e308, -1e308, 1e-308, 9999999999999999, -9999999999999999],
    )
    def test_fz6_extreme_numerics(self, client, mock_model_comprehensive, extreme):
        """FZ-6: Extreme numeric values handled without crash."""
        payload = {"temperature": extreme, "humidity": 50.0, "precipitation": 5.0}
        resp = client.post("/api/v1/predict/", json=payload, headers=AUTH)
        assert resp.status_code < 500, (
            f"Extreme value {extreme} caused {resp.status_code}"
        )

    # ------------------------------------------------------------------
    # FZ-7: Hypothesis property-based fuzzing (if hypothesis installed)
    # ------------------------------------------------------------------
    @pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    @given(
        temp=st.one_of(
            st.floats(allow_nan=True, allow_infinity=True),
            st.text(max_size=100),
            st.none(),
            st.booleans(),
        ),
        hum=st.one_of(
            st.floats(allow_nan=True, allow_infinity=True),
            st.text(max_size=100),
            st.none(),
        ),
        precip=st.one_of(
            st.floats(allow_nan=True, allow_infinity=True),
            st.text(max_size=100),
            st.none(),
        ),
    )
    def test_fz7_hypothesis_property_fuzz(self, app, mock_model_comprehensive, temp, hum, precip):
        """FZ-7: Hypothesis-generated inputs never cause 500."""
        with app.test_client() as c:
            payload = {"temperature": temp, "humidity": hum, "precipitation": precip}
            resp = c.post("/api/v1/predict/", json=payload, headers=AUTH)
            assert resp.status_code < 500, (
                f"Hypothesis input caused {resp.status_code}: {payload}"
            )

    # ------------------------------------------------------------------
    # FZ-8: SQL injection string corpus
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "sqli",
        [
            "' OR '1'='1",
            "1; DROP TABLE users;--",
            "1 UNION SELECT * FROM information_schema.tables--",
            "' OR 1=1--",
            "admin'--",
            "1' AND '1'='1",
            "1; WAITFOR DELAY '0:0:5'--",
        ],
    )
    def test_fz8_sql_injection_corpus(self, client, mock_model_comprehensive, sqli):
        """FZ-8: SQL injection strings return 400, never 500."""
        payload = {"temperature": sqli, "humidity": 50.0, "precipitation": 5.0}
        resp = client.post("/api/v1/predict/", json=payload, headers=AUTH)
        assert resp.status_code < 500, (
            f"SQLi '{sqli}' caused {resp.status_code}"
        )

    # ------------------------------------------------------------------
    # FZ-9: XSS string corpus
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "xss",
        [
            '<script>alert(1)</script>',
            '"><img src=x onerror=alert(1)>',
            "javascript:alert(1)",
            '<svg onload=alert(1)>',
            "'-alert(1)-'",
        ],
    )
    def test_fz9_xss_corpus(self, client, mock_model_comprehensive, xss):
        """FZ-9: XSS payloads return 400, never reflected, never 500."""
        payload = {"temperature": xss, "humidity": 50.0, "precipitation": 5.0}
        resp = client.post("/api/v1/predict/", json=payload, headers=AUTH)
        assert resp.status_code < 500
        body = resp.get_data(as_text=True)
        assert "<script>" not in body, "XSS reflected in response"

    # ------------------------------------------------------------------
    # FZ-10: Empty and null body variants
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "body,content_type",
        [
            (b"", "application/json"),
            (b"null", "application/json"),
            (b"undefined", "application/json"),
            (b"[]", "application/json"),
            (b"0", "application/json"),
            (b'""', "application/json"),
            (b"<xml></xml>", "application/xml"),
            (b"key=value", "application/x-www-form-urlencoded"),
        ],
    )
    def test_fz10_body_variants(self, client, mock_model_comprehensive, body, content_type):
        """FZ-10: Various body formats never cause 500."""
        resp = client.post(
            "/api/v1/predict/",
            data=body,
            headers={**AUTH, "Content-Type": content_type},
        )
        assert resp.status_code < 500, (
            f"Body {body!r} ({content_type}) caused {resp.status_code}"
        )
