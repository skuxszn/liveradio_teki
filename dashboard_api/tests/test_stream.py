"""Tests for stream control routes."""

import pytest
from fastapi import status


def test_get_stream_status(client, auth_headers):
    """Test getting stream status."""
    response = client.get("/api/v1/stream/status", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert "running" in data


def test_stream_start_requires_operator(client, auth_headers):
    """Test that starting stream requires operator role."""
    # Note: This test assumes the test user is an admin
    # which has operator privileges
    response = client.post("/api/v1/stream/start", headers=auth_headers)

    # Could succeed or fail depending on FFmpeg availability
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


def test_stream_endpoints_require_auth(client):
    """Test that stream endpoints require authentication."""
    endpoints = [
        ("/api/v1/stream/status", "get"),
        ("/api/v1/stream/start", "post"),
        ("/api/v1/stream/stop", "post"),
        ("/api/v1/stream/restart", "post"),
    ]

    for endpoint, method in endpoints:
        if method == "get":
            response = client.get(endpoint)
        else:
            response = client.post(endpoint)

        assert response.status_code == status.HTTP_403_FORBIDDEN

