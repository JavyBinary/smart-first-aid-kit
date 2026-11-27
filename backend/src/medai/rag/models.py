"""Data models for medical knowledge package, documents, and search results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "MedicineDocument",
    "MedicinePackage",
    "SearchResult",
]


class MedicineDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^D\d{2,3}$")
    title: str = Field(min_length=2)
    inn: str = Field(min_length=2)
    atc_code: str = Field(min_length=2)
    category: str = Field(min_length=2)
    forms: list[str] = Field(min_length=1)
    indications: list[str] = Field(min_length=1)
    contraindications: list[str] = Field(default_factory=list)
    dosage: str = Field(min_length=5)
    interactions: list[str] = Field(default_factory=list)
    emergency_flags: list[str] = Field(default_factory=list)

    def primary_text(self) -> str:
        """Primary clinical identity & indications text (excludes contraindications/interactions)."""
        parts = [
            self.title,
            self.inn,
            self.category,
            " ".join(self.forms),
            " ".join(self.indications),
            " ".join(self.emergency_flags),
        ]
        return " ".join(parts)

    def full_text(self) -> str:
        """Compose searchable text from title, inn, category, indications, and interactions."""
        parts = [
            self.title,
            self.inn,
            self.category,
            " ".join(self.forms),
            " ".join(self.indications),
            " ".join(self.contraindications),
            self.dosage,
            " ".join(self.interactions),
            " ".join(self.emergency_flags),
        ]
        return " ".join(parts)


class MedicinePackage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    medicines: list[MedicineDocument] = Field(min_length=1)


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    doc_id: str
    title: str
    score: float
    document: MedicineDocument
