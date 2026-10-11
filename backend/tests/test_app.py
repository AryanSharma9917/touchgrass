from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_reports_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_homepage_serves_frontend() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "TouchGrass" in response.text
    assert 'id="mission-form"' in response.text


def test_frontend_assets_are_served() -> None:
    response = client.get("/static/styles.css")

    assert response.status_code == 200
    assert ".planner" in response.text


def test_homepage_includes_mission_form_and_phone_free_view() -> None:
    response = client.get("/")

    assert 'name="available_time_minutes"' in response.text
    assert 'name="phone_free"' in response.text
    assert 'id="phone-free-view"' in response.text
