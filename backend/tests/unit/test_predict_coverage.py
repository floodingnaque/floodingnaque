import json
import os
from unittest.mock import MagicMock, mock_open, patch

import pytest
from app.services.predict import (
    ModelLoader,
    _load_model,
    compute_model_hmac_signature,
    get_current_model_info,
    get_latest_model_version,
    get_model_metadata,
    list_available_models,
    save_model_with_checksum,
    verify_model_hmac_signature,
)


class TestPredictCoverage:
    """Additional tests to improve code coverage for predict.py."""

    @pytest.fixture
    def mock_loader(self):
        ModelLoader.reset_instance()
        return ModelLoader.get_instance()

    def test_save_model_with_checksum_no_signing_key(self):
        """Test saving model without HMAC key."""
        mock_model = MagicMock()
        model_path = "test_model.joblib"
        metadata = {"version": 1}

        with (
            patch("app.services.predict.joblib.dump") as mock_dump,
            patch("app.services.predict.compute_model_checksum", return_value="checksum123") as mock_checksum,
            patch("app.services.predict._MODEL_SIGNING_KEY", ""),
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump") as mock_json_dump,
        ):

            checksum = save_model_with_checksum(mock_model, model_path, metadata)

            assert checksum == "checksum123"
            mock_dump.assert_called_once()
            # Verify metadata was updated
            assert metadata["checksum"] == "checksum123"
            assert "hmac_signature" not in metadata

    def test_save_model_with_checksum_with_signing_key(self):
        """Test saving model with HMAC key."""
        mock_model = MagicMock()
        model_path = "test_model.joblib"
        metadata = {"version": 1}

        with (
            patch("app.services.predict.joblib.dump") as mock_dump,
            patch("app.services.predict.compute_model_checksum", return_value="checksum123"),
            patch("app.services.predict._MODEL_SIGNING_KEY", "secret_key"),
            patch("app.services.predict.compute_model_hmac_signature", return_value="hmac123"),
            patch("builtins.open", mock_open()),
            patch("json.dump") as mock_json_dump,
        ):

            checksum = save_model_with_checksum(mock_model, model_path, metadata)

            assert checksum == "checksum123"
            assert metadata["hmac_signature"] == "hmac123"

    def test_save_model_hmac_computation_failure(self):
        """Test saving model when HMAC computation fails (should warn but proceed)."""
        mock_model = MagicMock()
        model_path = "test_model.joblib"
        metadata = {"version": 1}

        with (
            patch("app.services.predict.joblib.dump"),
            patch("app.services.predict.compute_model_checksum", return_value="checksum123"),
            patch("app.services.predict._MODEL_SIGNING_KEY", "secret_key"),
            patch("app.services.predict.compute_model_hmac_signature", side_effect=Exception("HMAC Error")),
            patch("builtins.open", mock_open()),
            patch("json.dump"),
        ):

            save_model_with_checksum(mock_model, model_path, metadata)

            assert "hmac_signature" not in metadata

    def test_verify_model_hmac_signature_valid(self):
        """Test valid HMAC verification."""
        with (
            patch("app.services.predict.compute_model_hmac_signature", return_value="valid_sig"),
            patch("app.services.predict.hmac.compare_digest", return_value=True),
        ):

            result = verify_model_hmac_signature("path", "valid_sig", "key")
            assert result is True

    def test_verify_model_hmac_signature_invalid(self):
        """Test invalid HMAC verification."""
        with (
            patch("app.services.predict.compute_model_hmac_signature", return_value="actual_sig"),
            patch("app.services.predict.hmac.compare_digest", return_value=False),
        ):

            result = verify_model_hmac_signature("path", "expected_sig", "key")
            assert result is False

    def test_verify_model_hmac_signature_missing_params(self):
        """Test HMAC verification with missing params."""
        assert verify_model_hmac_signature("path", "", "key") is False
        assert verify_model_hmac_signature("path", "sig", "") is False

    def test_verify_model_hmac_signature_exception(self):
        """Test assertion when computation raises exception."""
        with patch("app.services.predict.compute_model_hmac_signature", side_effect=Exception("Error")):
            assert verify_model_hmac_signature("path", "sig", "key") is False

    def test_compute_model_hmac_signature_no_key(self):
        """Test compute HMAC with empty key raises ValueError."""
        with pytest.raises(ValueError, match="MODEL_SIGNING_KEY is required"):
            compute_model_hmac_signature("path", "")

    def test_list_available_models(self):
        """Test listing models."""
        with patch("app.services.predict.Path") as MockPath:
            mock_path_obj = MagicMock()
            MockPath.return_value = mock_path_obj
            mock_path_obj.exists.return_value = True

            # Mock glob results
            mock_file1 = MagicMock()
            mock_file1.stem = "flood_rf_model_v1"
            mock_file1.__str__.return_value = "models/flood_rf_model_v1.joblib"

            mock_file2 = MagicMock()
            mock_file2.stem = "flood_rf_model_v2"
            mock_file2.__str__.return_value = "models/flood_rf_model_v2.joblib"

            mock_path_obj.glob.return_value = [mock_file1, mock_file2]

            with patch("app.services.predict.get_model_metadata") as mock_meta:
                mock_meta.side_effect = [{"version": 1}, {"version": 2}]

                models = list_available_models()

                assert len(models) == 2
                assert models[0]["version"] == 2  # Sorted reverse
                assert models[1]["version"] == 1

    def test_list_available_models_no_dir(self):
        """Test listing models when dir doesn't exist."""
        with patch("app.services.predict.Path") as MockPath:
            MockPath.return_value.exists.return_value = False
            assert list_available_models() == []

    def test_list_available_models_invalid_files(self):
        """Test listing skips invalid files."""
        with patch("app.services.predict.Path") as MockPath:
            mock_path_obj = MagicMock()
            MockPath.return_value = mock_path_obj
            mock_path_obj.exists.return_value = True

            mock_file = MagicMock()
            mock_file.stem = "invalid_name"  # Split fails or int fails
            mock_path_obj.glob.return_value = [mock_file]

            models = list_available_models()
            assert len(models) == 0

    def test_get_current_model_info_loaded(self, mock_loader):
        """Test getting info when model is loaded."""
        mock_model = MagicMock()
        mock_model.feature_names_in_ = ["f1", "f2"]
        mock_loader.set_model(mock_model, "path", {"v": 1}, "checksum")

        info = get_current_model_info()
        assert info["model_path"] == "path"
        assert info["integrity_verified"] is True
        assert info["features"] == ["f1", "f2"]

    def test_get_current_model_info_not_loaded_fails(self, mock_loader):
        """Test getting info when load fails."""
        mock_loader._model = None
        with patch("app.services.predict._load_model", side_effect=FileNotFoundError):
            assert get_current_model_info() is None

    def test_get_model_metadata_file_error(self):
        """Test get metadata handles file errors."""
        with patch("builtins.open", side_effect=IOError), patch("app.services.predict.Path.exists", return_value=True):
            assert get_model_metadata("path") is None

    def test_load_model_verify_integrity_false(self, mock_loader):
        """Test loading model with verify_integrity=False."""
        mock_loader._instance = None
        with (
            patch("app.services.predict.joblib.load") as mock_load,
            patch("app.services.predict.os.path.exists", return_value=True),
            patch("app.services.predict.get_model_metadata"),
            patch("app.services.predict.compute_model_checksum"),
        ):

            _load_model("path", verify_integrity=False)
            mock_load.assert_called_once()
            # Should NOT verify integrity

    def test_load_model_force_reload(self, mock_loader):
        """Test loading model with force_reload."""
        mock_loader.set_model(MagicMock(), "path", {}, "sum")

        with (
            patch("app.services.predict.joblib.load") as mock_load,
            patch("app.services.predict.os.path.exists", return_value=True),
            patch("app.services.predict.get_model_metadata"),
            patch("app.services.predict.compute_model_checksum"),
            patch("app.services.predict.verify_model_integrity", return_value=True),
        ):

            _load_model("path", force_reload=True)
            mock_load.assert_called()

    def test_get_latest_model_version(self):
        """Test get latest version."""
        with patch("app.services.predict.list_available_models", return_value=[{"version": 5}]):
            assert get_latest_model_version() == 5

        with (
            patch("app.services.predict.list_available_models", return_value=[]),
            patch("app.services.predict.Path.exists", return_value=True),
            patch("app.services.predict.get_model_metadata", return_value={"version": 3}),
        ):
            # Fallback to single file
            assert get_latest_model_version() == 3

    def test_get_latest_model_version_none(self):
        """Test get latest version returns None."""
        with (
            patch("app.services.predict.list_available_models", return_value=[]),
            patch("app.services.predict.Path.exists", return_value=False),
        ):
            assert get_latest_model_version() is None
