import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pytest
from unittest.mock import patch, MagicMock
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"URL Shortener" in response.data


def test_shorten_url_success(client):
    mock_redis = MagicMock()
    mock_redis.exists.return_value = False

    with patch("app.get_redis", return_value=mock_redis):
        response = client.post("/shorten", data={"url": "https://www.google.com"})

    assert response.status_code == 200
    mock_redis.set.assert_called_once()


def test_shorten_url_adds_https(client):
    mock_redis = MagicMock()
    mock_redis.exists.return_value = False

    with patch("app.get_redis", return_value=mock_redis):
        response = client.post("/shorten", data={"url": "google.com"})

    assert response.status_code == 200
    args = mock_redis.set.call_args[0]
    assert args[1].startswith("https://")


def test_shorten_empty_url_returns_400(client):
    response = client.post("/shorten", data={"url": ""})
    assert response.status_code == 400


def test_redirect_existing_url(client):
    mock_redis = MagicMock()
    mock_redis.get.return_value = "https://www.google.com"

    with patch("app.get_redis", return_value=mock_redis):
        response = client.get("/abc123")

    assert response.status_code == 302
    assert response.location == "https://www.google.com"


def test_redirect_nonexistent_code(client):
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with patch("app.get_redis", return_value=mock_redis):
        response = client.get("/doesnotexist")

    assert response.status_code == 404


def test_health_endpoint_redis_up(client):
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True

    with patch("app.get_redis", return_value=mock_redis):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["redis"] == "connected"


def test_health_endpoint_redis_down(client):
    mock_redis = MagicMock()
    mock_redis.ping.side_effect = Exception("Connection refused")

    with patch("app.get_redis", return_value=mock_redis):
        response = client.get("/health")

    assert response.status_code == 503
    data = response.get_json()
    assert data["status"] == "unhealthy"