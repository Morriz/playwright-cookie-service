"""Unit tests for webhook receiver and Pydantic models."""

import pytest
from fastapi.testclient import TestClient

from models import WebhookPayload
from webhook_receiver import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_webhook_success(client):
    """Test webhook endpoint with successful authentication."""
    payload = {
        "success": True,
        "cookies": "guest_id=test123; ct0=abc; twid=u%3D123",
        "error": None,
        "iterations": 12,
        "request_id": "test-request-123",
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200


def test_webhook_failure(client):
    """Test webhook endpoint with failed authentication."""
    payload = {
        "success": False,
        "cookies": None,
        "error": "Login failed",
        "iterations": 5,
        "request_id": "test-request-456",
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200


def test_webhook_payload_accepts_none_values():
    """Test that WebhookPayload model accepts None for optional fields."""
    # This was the bug: Pydantic rejected None values
    payload = WebhookPayload(
        success=False,
        cookies=None,
        error="Login failed",
        iterations=None,
        request_id="test-123",
    )

    assert payload.success is False
    assert payload.cookies is None
    assert payload.error == "Login failed"
    assert payload.iterations is None
    assert payload.request_id == "test-123"


def test_webhook_payload_success_case():
    """Test WebhookPayload for successful authentication."""
    payload = WebhookPayload(
        success=True,
        cookies="auth_token=xyz; ct0=abc",
        error=None,
        iterations=10,
        request_id="test-456",
    )

    assert payload.success is True
    assert payload.cookies == "auth_token=xyz; ct0=abc"
    assert payload.error is None
    assert payload.iterations == 10
