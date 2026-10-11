"""Local Ollama-powered outdoor mission generation."""

import json

import httpx
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.models import Mission, MissionRequest

SYSTEM_PROMPT = """\
You create practical outdoor missions that help people spend time in the real
world. Return only JSON matching the supplied schema. Respect every user
constraint and the available time. Set estimated_duration to the exact time
provided, and give every step a duration_minutes and an instruction. The step
durations must add up exactly to estimated_duration. Create three to five
simple, concrete steps with realistic time allocations and no rushed sequence.
Any optional challenge must fit within those steps and add no extra time.
Include steps that can be remembered without repeatedly checking a phone.
Prefer ordinary surroundings and no special equipment. Treat the user's
constraints as requirements, not suggestions; do not contradict, weaken, or
ignore them.
Never suggest climbing, entering restricted areas, unsafe road crossing,
swimming, risky wildlife contact, or activities that depend on unknown weather.
Do not give medical advice or claim an activity is medically safe. Include
concise safety notes reminding the user to follow local rules and conditions.
Keep the mission calm, inclusive, and suitable for the stated energy level.
Use plain text only: no Markdown, numbering prefixes, or generic fitness
benefits. If phone_free is true, do not use or require a phone, camera, or any
other screen during any activity step. Encourage the user to put their phone
away and enjoy being outside.
"""


class MissionGenerationError(Exception):
    """Base error for mission generation failures."""

    status_code = 502
    code = "mission_generation_failed"
    message = "Could not generate a mission right now."

    def __init__(self) -> None:
        super().__init__(self.message)


class OllamaUnavailableError(MissionGenerationError):
    status_code = 503
    code = "ollama_unavailable"
    message = "Ollama is unavailable. Start Ollama and try again."


class OllamaModelNotFoundError(MissionGenerationError):
    status_code = 503
    code = "ollama_model_not_found"
    message = "The configured Ollama model is not installed."


class OllamaTimeoutError(MissionGenerationError):
    status_code = 504
    code = "ollama_timeout"
    message = "Mission generation timed out. Try again."


class InvalidModelResponseError(MissionGenerationError):
    status_code = 502
    code = "invalid_model_response"
    message = "The local model returned an invalid mission. Try again."


async def generate_mission(
    request: MissionRequest, settings: Settings | None = None
) -> Mission:
    """Generate and validate an outdoor mission using the configured Ollama model."""
    active_settings = settings or get_settings()
    payload = {
        "model": active_settings.ollama_model,
        "system": SYSTEM_PROMPT,
        "format": Mission.model_json_schema(),
        "stream": False,
    }
    prompt_data: dict[str, object] = {
        "preferences": request.model_dump(),
        "schedule_requirement": (
            f"Set estimated_duration to {request.available_time_minutes} minutes. "
            f"The sum of every step's duration_minutes must be exactly "
            f"{request.available_time_minutes}."
        ),
    }
    last_validation_error: Exception | None = None

    try:
        async with httpx.AsyncClient(
            timeout=active_settings.ollama_timeout_seconds
        ) as client:
            for attempt in range(2):
                if last_validation_error is not None:
                    prompt_data["correction"] = (
                        "Your previous response did not satisfy the required "
                        "mission schema or exact schedule. Regenerate the full "
                        "mission and correct the schedule."
                    )
                payload["prompt"] = json.dumps(prompt_data, ensure_ascii=False)
                response = await client.post(
                    f"{active_settings.ollama_base_url}/api/generate",
                    json=payload,
                )

                if response.status_code == 404:
                    try:
                        error_payload = response.json()
                        error_value = (
                            error_payload.get("error")
                            if isinstance(error_payload, dict)
                            else None
                        )
                        error_text = (
                            error_value.lower()
                            if isinstance(error_value, str)
                            else ""
                        )
                    except ValueError:
                        error_text = ""
                    if "model" in error_text and "not found" in error_text:
                        raise OllamaModelNotFoundError()
                    raise OllamaUnavailableError()
                if response.is_error:
                    raise OllamaUnavailableError()

                try:
                    ollama_result = response.json()
                    model_output = ollama_result["response"]
                    if not isinstance(model_output, str):
                        raise TypeError("Ollama response field must be a string")
                    mission = Mission.model_validate_json(model_output)
                    if mission.estimated_duration != request.available_time_minutes:
                        raise ValueError("mission duration does not match request")
                    return mission
                except (ValueError, TypeError, KeyError, ValidationError) as exc:
                    last_validation_error = exc
                    if attempt == 1:
                        raise InvalidModelResponseError() from exc
    except httpx.TimeoutException as exc:
        raise OllamaTimeoutError() from exc
    except httpx.ConnectError as exc:
        raise OllamaUnavailableError() from exc
    except httpx.RequestError as exc:
        raise OllamaUnavailableError() from exc

    raise InvalidModelResponseError() from last_validation_error
