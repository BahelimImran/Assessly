import re
import logging

logger = logging.getLogger(__name__)

SMALL_TALK = {"hi", "hello", "hey", "how are you"}
MATH_PATTERN = r"\b\d+(\.\d+)?\s*[\+\-\*/]\s*\d+(\.\d+)?\b"

GENERAL_KNOWLEDGE = [
    "what is", "who is", "define", "physics", "math", "ohm"
]

DOMAIN_KEYWORDS = [
    "wireline", "toolstring", "perforation", "well",
    "logging", "cable", "depth", "pressure",
    "completion", "slickline"
]


def rule_based_router(query: str):
    q = query.lower()

    if any(w in q for w in SMALL_TALK):
        return {"route": "NO_RAG", "confidence": 0.9, "reason": "small_talk"}

    if re.search(MATH_PATTERN, q):
        return {"route": "NO_RAG", "confidence": 0.95, "reason": "math"}

    if any(w in q for w in DOMAIN_KEYWORDS):
        return {"route": "RAG", "confidence": 0.85, "reason": "domain_keyword"}

    if any(w in q for w in GENERAL_KNOWLEDGE):
        return {"route": "NO_RAG", "confidence": 0.7, "reason": "general_knowledge"}

    return {"route": "UNKNOWN", "confidence": 0.5, "reason": "uncertain"}