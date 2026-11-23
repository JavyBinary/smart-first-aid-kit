"""Domain models for user health profile (medical card)."""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

__all__ = ["HealthProfile", "UpdateHealthProfileRequest"]


class HealthProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    age: int = Field(default=25, ge=0, le=130)
    weight_kg: float = Field(default=70.0, ge=1.0, le=300.0)
    chronic_diseases: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("chronic_diseases", "chronic"),
    )
    allergies: list[str] = Field(default_factory=list)
    special_notes: str | None = None


class UpdateHealthProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    age: int | None = Field(default=None, ge=0, le=130)
    weight_kg: float | None = Field(default=None, ge=1.0, le=300.0)
    chronic_diseases: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("chronic_diseases", "chronic"),
    )
    allergies: list[str] | None = None
    special_notes: str | None = None
