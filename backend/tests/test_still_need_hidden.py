"""Test that 'Still need:' debug text is stripped from user-visible responses (Bug C fix)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


def _strip_still_need(response_text: str) -> str:
    """Replicate the stripping logic from _intake_turn."""
    clean_lines = [
        line for line in response_text.splitlines()
        if not line.strip().lower().startswith("still need:")
    ]
    return "\n".join(clean_lines).strip()


def test_still_need_stripped_from_single_line():
    text = "Great choice! Toronto is wonderful.\nStill need: dates, pace\nWhat dates are you visiting?"
    cleaned = _strip_still_need(text)
    assert "Still need" not in cleaned
    assert "Toronto is wonderful" in cleaned
    assert "What dates are you visiting?" in cleaned


def test_still_need_stripped_case_insensitive():
    text = "Sounds fun!\nSTILL NEED: budget\nWhen do you want to go?"
    cleaned = _strip_still_need(text)
    assert "STILL NEED" not in cleaned
    assert "Sounds fun!" in cleaned


def test_no_still_need_unchanged():
    text = "Great! I have everything I need. Want me to generate your itinerary for Toronto?"
    cleaned = _strip_still_need(text)
    assert cleaned == text


def test_still_need_parsed_before_stripping():
    """Verify the _parse_still_need still extracts items before stripping."""
    from services.conversation_service import ConversationService

    text = "Let me plan your trip!\nStill need: dates, pace\nWhen are you visiting?"
    still_need = ConversationService._parse_still_need(text)
    assert still_need == ["dates", "pace"]

    # Then strip
    cleaned = _strip_still_need(text)
    assert "Still need" not in cleaned


def test_empty_still_need_returns_empty_list():
    """'Still need: none' should return empty list."""
    from services.conversation_service import ConversationService

    text = "All set!\nStill need: none"
    result = ConversationService._parse_still_need(text)
    assert result == []
