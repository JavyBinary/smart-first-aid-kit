"""Two-layer Input and Output Guardrails for MedAI clinical safety."""

from __future__ import annotations

import re

from medai.rag.analyzer import normalize_text
from medai.rag.models import SearchResult

__all__ = [
    "EMERGENCY_KEYWORDS",
    "OUT_OF_DOMAIN_KEYWORDS",
    "OUT_OF_DOMAIN_RESPONSE",
    "PROMPT_INJECTION_RESPONSE",
    "detect_prompt_injection",
    "is_emergency_query",
    "is_out_of_domain_query",
    "verify_output_grounding",
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
    "футбол",
    "курс доллар",
)

INJECTION_PATTERNS = (
    re.compile(r"игнорируй\s+(все\s+)?(предыдущие|системные)\s+(инструкции|правила)", re.I),
    re.compile(r"забудь\s+(все\s+)?(инструкции|правила)", re.I),
    re.compile(r"(выведи|покажи|раскрой)\s+(системный\s+)?промпт", re.I),
    re.compile(r"ignore\s+(all\s+)?(previous|prior|system)\s+(instructions|rules|prompts?)", re.I),
    re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"ты\s+теперь\s+(пират|хакер|повар|программист)", re.I),
)

OUT_OF_DOMAIN_RESPONSE = (
    "Я медицинский ассистент MedAI и специализируюсь исключительно на вопросах здоровья, "
    "доврачебной помощи и препаратах домашней аптечки.\n\n"
    "Я не могу проконсультировать по кулинарным, бытовым или техническим темам, "
    "но с радостью отвечу на вопросы о симптомах, медикаментах и оказании первой помощи."
)

PROMPT_INJECTION_RESPONSE = (
    "Обнаружена попытка переопределить системные инструкции безопасности ассистента MedAI. "
    "Запрос отклонен. Пожалуйста, сформулируйте вопрос о симптомах или препаратах домашней аптечки."
)


def is_emergency_query(text: str) -> bool:
    """Return True if text contains critical emergency symptoms requiring immediate 112."""
    lower = text.lower()
    return any(kw in lower for kw in EMERGENCY_KEYWORDS)


def detect_prompt_injection(text: str) -> bool:
    """Detect common prompt-injection / jailbreak patterns on input."""
    return any(pattern.search(text) for pattern in INJECTION_PATTERNS)


def is_out_of_domain_query(text: str) -> bool:
    """Return True if text is explicitly out of health/medical scope."""
    lower = text.lower()
    for kw in OUT_OF_DOMAIN_KEYWORDS:
        if re.search(r"\b" + re.escape(kw), lower):
            return True
    return False


def verify_output_grounding(answer: str, sources: list[SearchResult]) -> bool:
    """Output Guardrail: verify that answer dosages/facts align with retrieved docs."""
    norm_ans = normalize_text(answer)
    if not norm_ans or not sources:
        return True
    context_tokens = set(
        normalize_text(" ".join(s.document.full_text() for s in sources)).split()
    )
    # Check that numerical dosages mentioned alongside 'мг' in answer appear in context
    dosages_in_answer = re.findall(r"(\d+)\s*мг", norm_ans)
    if not dosages_in_answer:
        return True
    context_raw = normalize_text(" ".join(s.document.dosage + " " + " ".join(s.document.forms) for s in sources))
    for num in dosages_in_answer:
        if num not in context_raw and num not in context_tokens:
            return False
    return True
