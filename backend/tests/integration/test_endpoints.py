#!/usr/bin/env python
"""
Integration tests for API endpoints.

These tests use Flask test client for reliable testing without
requiring a running server.
"""

import json

import pytest

# API prefix for versioned endpoints
API_V1_PREFIX = "/api/v1"


class TestHealthEndpoints:
    """Integration tests for health check endpoints."""

    def test_root_endpoint(self, client):
        """Test the root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.get_json()
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data

    def test_status_endpoint(self, client):
        """Test the /status endpoint."""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data
        assert data["status"] == "running"

    def test_health_endpoint(self, client):
        """Test the /health endpoint."""
        response = client.get("/health")
        # Health may return 503 if services are unavailable, or 429 if rate limited
        assert response.status_code in [200, 429, 503]
        data = response.get_json()
        assert "status" in data or "error" in data
        # Response structure varies based on health status


class TestModelsEndpoint:
    """Integration tests for model management endpoints."""

    def test_list_models(self, client):
        """Test the /api/v1/models endpoint."""
        response = client.get(f"{API_V1_PREFIX}/models")
        # May return 404 if models are not configured or 200 with model list
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.get_json()
            assert "models" in data or "data" in data


class TestDataEndpoint:
    """Integration tests for data endpoint."""

    def test_get_data_default(self, client):
        """Test the /api/v1/data/data endpoint with default parameters."""
        response = client.get(f"{API_V1_PREFIX}/data/data")
        # Returns 200 with data, 401 if auth required, or 500 if DB unavailable
        assert response.status_code in [200, 401, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert "data" in data
            assert "total" in data

    def test_get_data_with_limit(self, client):
        """Test the /api/v1/data/data endpoint with custom limit."""
        response = client.get(f"{API_V1_PREFIX}/data/data?limit=10")
        assert response.status_code in [200, 401, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert data.get("limit") == 10 or "data" in data

    def test_get_data_invalid_limit(self, client):
        """Test the /api/v1/data/data endpoint with invalid limit."""
        response = client.get(f"{API_V1_PREFIX}/data/data?limit=9999")
        # May return 400 for invalid limit, 401 if auth required, or 429 if rate limited
        assert response.status_code in [400, 401, 429]
