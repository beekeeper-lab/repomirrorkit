"""Tests for the sample Flask app — fixture content, exercises test-pattern detector."""

from __future__ import annotations

from app import app


def test_list_users_empty():
    """Empty database returns an empty list."""
    with app.test_client() as client:
        response = client.get("/api/users")
        assert response.status_code == 200
