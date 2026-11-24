"""Guardrails and domain classification for MedAI dialogs."""

from __future__ import annotations

import re

__all__ = [
    "EMERGENCY_KEYWORDS",
    "OUT_OF_DOMAIN_KEYWORDS",
    "OUT_OF_DOMAIN_RESPONSE",
    "is_emergency_query",
    "is_out_of_domain_query",
]

EMERGENCY_KEYWORDS = (
    "ожог",
    "ожоги",
    "кипятком",
    "кровотечение",
    "потеря сознания",
    "без сознания",
    "судороги",
    "удушье",
    "задыхается",
    "инфаркт",
    "инсульт",
    "паралич",
    "анафилаксия",
    "отек квинке",
)

OUT_OF_DOMAIN_KEYWORDS = (
    "блин",
    "блины",
    "рецепт",
    "готовить",
    "приготовить",
    "пирог",
    "суп",
    "выпечк",
    "программ",
    "питон",
    "python",
    "javascript",
    "код",
    "стих",
    "анекдот",
    "президент",
    "погода",
    "криптовалют",
    "биткоин",
)

OUT_OF_DOMAIN_RESPONSE = (
    "Я медицинский ассистент MedAI и специализируюсь исключительно на вопросах здоровья, "
    "доврачебной помощи и препаратах домашней аптечки.\n\n"
    "Я не могу проконсультировать по кулинарным, бытовым или техническим темам, "
    "но с радостью отвечу на вопросы о симптомах, медикаментах и оказании первой помощи."
)


def is_emergency_query(text: str) -> bool:
    """Return True if text contains critical emergency symptoms requiring immediate 112."""
    lower = text.lower()
    return any(kw in lower for kw in EMERGENCY_KEYWORDS)


def is_out_of_domain_query(text: str) -> bool:
    """Return True if text is explicitly out of health/medical scope."""
    lower = text.lower()
    # Check explicitly non-medical keywords
    for kw in OUT_OF_DOMAIN_KEYWORDS:
        if re.search(r"\b" + re.escape(kw), lower):
            return True
    return False
