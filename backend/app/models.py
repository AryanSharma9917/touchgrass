"""Validated mission request and response models."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ShortText = Annotated[str, Field(min_length=1, max_length=80)]


class MissionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    available_time_minutes: int = Field(ge=5, le=180)
    preferred_activity: str = Field(min_length=2, max_length=80)
    energy_level: Literal["low", "moderate", "high"]
    environment: str = Field(min_length=2, max_length=80)
    interests: list[ShortText] = Field(default_factory=list, max_length=8)
    constraints: list[ShortText] = Field(default_factory=list, max_length=8)
    phone_free: bool = True


class MissionStep(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    duration_minutes: int = Field(ge=1, le=180)
    instruction: str = Field(min_length=5, max_length=240)


class Mission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=100)
    short_description: str = Field(min_length=5, max_length=240)
    estimated_duration: int = Field(ge=5, le=180)
    preparation: list[str] = Field(default_factory=list, max_length=5)
    steps: list[MissionStep] = Field(min_length=2, max_length=6)
    optional_challenge: str | None = Field(default=None, max_length=240)
    safety_notes: list[str] = Field(min_length=1, max_length=5)
    completion_message: str = Field(min_length=3, max_length=160)

    @model_validator(mode="after")
    def step_durations_match_mission(self) -> "Mission":
        total_step_minutes = sum(step.duration_minutes for step in self.steps)
        if total_step_minutes != self.estimated_duration:
            raise ValueError(
                "step durations must add up to the estimated mission duration"
            )
        return self
