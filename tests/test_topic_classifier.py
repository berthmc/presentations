"""Tests for IT topic classification and technology extraction."""

from presentations.services.topic_classifier import extract_technologies, is_it_topic


def test_is_it_topic_detects_speech_architecture_brief() -> None:
    brief = (
        "Topic: Real-Time AI Speech-to-Speech Architecture\n"
        "Audience: Enterprise architects\n"
        "Goal: Explain latency and codec trade-offs"
    )
    assert is_it_topic(brief) is True


def test_is_it_topic_rejects_non_technical_brief() -> None:
    brief = "Topic: Gardening in the Ardennes\nAudience: Home gardeners"
    assert is_it_topic(brief) is False


def test_extract_technologies_finds_known_names() -> None:
    brief = (
        "Topic: Real-Time AI Speech-to-Speech Architecture using WebRTC and Azure Speech SDK\n"
        "Key points:\n- OpenAI Whisper transcription"
    )
    techs = extract_technologies(brief, max_items=5)
    assert "WebRTC" in techs
    assert "Azure Speech SDK" in techs
    assert "OpenAI Whisper" in techs


def test_extract_technologies_falls_back_to_topic_line() -> None:
    brief = "Topic: Kubernetes platform migration\nAudience: Platform engineers"
    techs = extract_technologies(brief, max_items=3)
    assert techs
    assert any("Kubernetes" in tech for tech in techs)
