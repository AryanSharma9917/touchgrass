import asyncio
import json
from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.models import MissionRequest
from app.services.mission_generator import (
    InvalidModelResponseError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    OllamaUnavailableError,
    generate_mission,
)

client = TestClient(app)

REQUEST_DATA = {
    "available_time_minutes": 45,
    "preferred_activity": "walking",
    "energy_level": "low",
    "environment": "park",
    "interests": ["nature", "photography"],
    "constraints": ["stay on flat paths"],
    "phone_free": True,
}

MISSION_DATA = {
    "title": "A Gentle Park Reset",
    "short_description": "Take an easy walk and notice small details.",
    "estimated_duration": 45,
    "preparation": ["Wear comfortable shoes."],
    "steps": [
        {
            "duration_minutes": 15,
            "instruction": "Walk slowly along a familiar, flat path.",
        },
        {
            "duration_minutes": 5,
            "instruction": "Pause and notice three natural details.",
        },
        {
            "duration_minutes": 25,
            "instruction": "Continue your easy walk on the flat path.",
        },
    ],
    "optional_challenge": "Notice a sound you usually overlook.",
    "safety_notes": ["Stay on public paths and watch your surroundings."],
    "completion_message": "Take one moment to remember what you noticed.",
}

SETTINGS = Settings(
    ollama_base_url="http://ollama.test",
    ollama_model="gemma3:4b",
    ollama_timeout_seconds=4,
)


def run_generation(
    handler: Callable[[httpx.Request], httpx.Response],
):
    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def mock_transport_client(*args, **kwargs):
        return original_client(transport=transport, *args, **kwargs)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "app.services.mission_generator.httpx.AsyncClient",
            mock_transport_client,
        )
        return asyncio.run(
            generate_mission(MissionRequest.model_validate(REQUEST_DATA), SETTINGS)
        )


def test_generate_mission_sends_preferences_and_validates_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url == "http://ollama.test/api/generate"
        assert payload["model"] == "gemma3:4b"
        assert payload["stream"] is False
        assert payload["format"]["type"] == "object"
        prompt_data = json.loads(payload["prompt"])
        assert prompt_data["preferences"]["constraints"] == ["stay on flat paths"]
        assert prompt_data["preferences"]["phone_free"] is True
        assert "sum of every step's duration_minutes must be exactly 45" in (
            prompt_data["schedule_requirement"]
        )
        assert "durations must add up exactly" in payload["system"]
        assert "do not use or require a phone" in payload["system"]
        return httpx.Response(200, json={"response": json.dumps(MISSION_DATA)})

    mission = run_generation(handler)

    assert mission.title == "A Gentle Park Reset"
    assert mission.estimated_duration == 45
    assert len(mission.steps) == 3


def test_generate_mission_rejects_malformed_model_output() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": '{"title": "incomplete"}'})

    with pytest.raises(InvalidModelResponseError):
        run_generation(handler)


def test_generate_mission_rejects_wrong_duration() -> None:
    wrong_duration = {**MISSION_DATA, "estimated_duration": 30}

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": json.dumps(wrong_duration)})

    with pytest.raises(InvalidModelResponseError):
        run_generation(handler)


def test_generate_mission_rejects_steps_that_do_not_fill_time() -> None:
    invalid_schedule = {
        **MISSION_DATA,
        "steps": [
            *MISSION_DATA["steps"][:-1],
            {
                "duration_minutes": 24,
                "instruction": "Continue your easy walk on the flat path.",
            },
        ],
    }

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": json.dumps(invalid_schedule)})

    with pytest.raises(InvalidModelResponseError):
        run_generation(handler)


def test_generate_mission_retries_invalid_schedule_once() -> None:
    responses = iter(
        [
            {
                **MISSION_DATA,
                "steps": [
                    *MISSION_DATA["steps"][:-1],
                    {
                        "duration_minutes": 24,
                        "instruction": "Continue your easy walk on the flat path.",
                    },
                ],
            },
            MISSION_DATA,
        ]
    )
    prompts = []

    def handler(request: httpx.Request) -> httpx.Response:
        prompts.append(json.loads(request.content)["prompt"])
        return httpx.Response(200, json={"response": json.dumps(next(responses))})

    mission = run_generation(handler)

    assert mission.estimated_duration == 45
    assert len(prompts) == 2
    assert "correction" in json.loads(prompts[1])


def test_generate_mission_reports_missing_ollama_model() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'gemma3:4b' not found"})

    with pytest.raises(OllamaModelNotFoundError):
        run_generation(handler)


def test_generate_mission_reports_ollama_unavailable() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(OllamaUnavailableError):
        run_generation(handler)


def test_generate_mission_reports_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(OllamaTimeoutError):
        run_generation(handler)


def test_mission_endpoint_returns_generated_mission(monkeypatch) -> None:
    async def fake_generate_mission(request: MissionRequest):
        assert request.available_time_minutes == 45
        return MISSION_DATA

    monkeypatch.setattr("app.main.generate_mission", fake_generate_mission)

    response = client.post("/api/missions", json=REQUEST_DATA)

    assert response.status_code == 200
    assert response.json()["title"] == "A Gentle Park Reset"
    assert sum(
        step["duration_minutes"] for step in response.json()["steps"]
    ) == 45


@pytest.mark.parametrize(
    "overrides",
    [
        {"available_time_minutes": -1},
        {"available_time_minutes": 181},
        {"energy_level": "exhausted"},
        {"environment": ""},
    ],
)
def test_mission_endpoint_rejects_invalid_request(overrides) -> None:
    response = client.post("/api/missions", json={**REQUEST_DATA, **overrides})

    assert response.status_code == 422


def test_mission_endpoint_returns_actionable_model_error(monkeypatch) -> None:
    async def fake_generate_mission(_: MissionRequest):
        raise OllamaModelNotFoundError()

    monkeypatch.setattr("app.main.generate_mission", fake_generate_mission)

    response = client.post("/api/missions", json=REQUEST_DATA)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ollama_model_not_found"
