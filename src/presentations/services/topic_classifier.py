"""Detect IT topics and extract technology names from presentation briefs."""

from __future__ import annotations

import re

IT_KEYWORDS: frozenset[str] = frozenset(
    {
        "ai",
        "api",
        "architecture",
        "aws",
        "azure",
        "cloud",
        "codec",
        "container",
        "database",
        "devops",
        "docker",
        "endpoint",
        "ffmpeg",
        "framework",
        "gcp",
        "gpu",
        "grpc",
        "infrastructure",
        "kubernetes",
        "latency",
        "llm",
        "microservice",
        "ml",
        "model",
        "network",
        "nlp",
        "openai",
        "pipeline",
        "protocol",
        "real-time",
        "realtime",
        "sdk",
        "serverless",
        "software",
        "speech",
        "streaming",
        "system",
        "technical",
        "technology",
        "transformer",
        "vertex",
        "voice",
        "webrtc",
        "websocket",
    }
)

KNOWN_TECHNOLOGIES: tuple[str, ...] = (
    "Azure Cognitive Services Speech",
    "Azure OpenAI",
    "Azure Speech SDK",
    "Docker",
    "FastAPI",
    "Google Cloud",
    "Google Vertex AI",
    "Kubernetes",
    "OpenAI Whisper",
    "WebRTC",
    "ffmpeg",
    "gRPC",
    "Kubernetes",
    "Node.js",
    "Python",
    "React",
    "TensorFlow",
    "PyTorch",
    "Redis",
    "PostgreSQL",
    "MongoDB",
    "Kafka",
    "RabbitMQ",
    "Terraform",
    "Helm",
    "Prometheus",
    "Grafana",
    "Ollama",
    "Gemini",
    "LangChain",
    "Hugging Face",
)

_ACRONYM_PATTERN = re.compile(r"\b[A-Z]{2,}(?:[-/][A-Z0-9]+)*\b")
_TECH_TOKEN_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,4}\b")


def _normalise_brief(brief: str) -> str:
    return brief.strip().lower()


def is_it_topic(brief: str) -> bool:
    """Return True when the brief appears to describe an IT or technical topic."""
    text = _normalise_brief(brief)
    if not text:
        return False

    tokens = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text)
    if any(token in IT_KEYWORDS for token in tokens):
        return True

    if any(keyword.replace("-", " ") in text for keyword in IT_KEYWORDS if "-" in keyword):
        return True

    return bool(_ACRONYM_PATTERN.search(brief))


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _topic_line(brief: str) -> str:
    for line in brief.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("topic:"):
            return stripped.split(":", 1)[1].strip()
    return brief.strip().splitlines()[0] if brief.strip() else ""


def extract_technologies(brief: str, *, max_items: int = 3) -> list[str]:
    """Extract likely technology or product names from a brief."""
    if not brief.strip():
        return []

    found: list[str] = []
    brief_lower = brief.casefold()

    for tech in KNOWN_TECHNOLOGIES:
        if tech.casefold() in brief_lower:
            found.append(tech)

    for match in _ACRONYM_PATTERN.findall(brief):
        if match.lower() not in IT_KEYWORDS and len(match) >= 2:
            found.append(match)

    for match in _TECH_TOKEN_PATTERN.findall(brief):
        candidate = match.strip()
        if len(candidate) < 3:
            continue
        if candidate.lower() in IT_KEYWORDS:
            continue
        if candidate.endswith(("Topic", "Audience", "Goal", "Tone", "Target", "Key")):
            continue
        found.append(candidate)

    if not found and is_it_topic(brief):
        topic = _topic_line(brief)
        if topic:
            found.append(topic)

    return _dedupe_preserve_order(found)[:max_items]
