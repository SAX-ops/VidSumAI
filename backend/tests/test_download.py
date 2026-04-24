import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_parse_endpoint():
    response = client.post(
        "/api/parse",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "formats" in data
    assert len(data["formats"]) > 0


def test_parse_endpoint_invalid_url():
    response = client.post(
        "/api/parse",
        json={"url": "invalid-url"}
    )
    assert response.status_code == 400
