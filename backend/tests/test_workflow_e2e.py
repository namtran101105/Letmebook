"""
End-to-end workflow test using mocked LLM responses.

Verifies the full conversation flow:
    greeting → intake → confirmed → itinerary

No real API calls are made — LLM responses are mocked.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_groq_mock(responses):
    """Return a mock GroqClient whose chat_with_history cycles through responses."""
    mock = MagicMock()
    mock.chat_with_history = MagicMock(side_effect=responses)
    return mock


# ---------------------------------------------------------------------------
# Phase transition tests
# ---------------------------------------------------------------------------

def test_greeting_returns_correct_phase():
    """First call with empty messages should return greeting phase."""
    from services.conversation_service import ConversationService

    svc = ConversationService.__new__(ConversationService)
    svc.use_groq = False
    svc.use_gemini = False
    svc.venue_service = None
    svc.orchestrator = None

    messages, text, phase, still_need, enrichment = svc._greeting()

    assert phase == "greeting"
    assert "Toronto" in text or "trip" in text.lower() or "travel" in text.lower()
    assert still_need is not None  # Should list required fields
    assert enrichment is None


def test_confirmation_marker_present_in_system_prompt():
    """Ensure the confirmation phrase is in the intake prompt."""
    from services.conversation_service import INTAKE_SYSTEM_PROMPT, _CONFIRMATION_MARKER
    assert _CONFIRMATION_MARKER.lower() in INTAKE_SYSTEM_PROMPT.lower(), (
        "CRITICAL: confirmation marker not in system prompt — itinerary can never be triggered!"
    )


@pytest.mark.asyncio
async def test_intake_turn_strips_still_need():
    """_intake_turn must strip 'Still need:' lines from visible response."""
    from services.conversation_service import ConversationService

    groq_mock = _make_groq_mock([
        "Great! I have Toronto noted.\nStill need: dates, pace\nWhen are you planning to visit?"
    ])

    svc = ConversationService.__new__(ConversationService)
    svc.use_groq = True
    svc.use_gemini = False
    svc.groq_client = groq_mock
    svc.venue_service = None
    svc.orchestrator = None

    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "I want to visit Toronto"},
    ]
    updated_msgs, text, phase, still_need, enrichment = await svc._intake_turn(messages)

    assert "Still need" not in text
    assert "Toronto" in text
    assert still_need == ["dates", "pace"]


@pytest.mark.asyncio
async def test_intake_transitions_to_confirmed():
    """When LLM includes confirmation marker, phase becomes 'confirmed'."""
    from services.conversation_service import ConversationService, _CONFIRMATION_MARKER

    groq_mock = _make_groq_mock([
        f"Perfect! Want me to generate your itinerary for Toronto?"
    ])

    svc = ConversationService.__new__(ConversationService)
    svc.use_groq = True
    svc.use_gemini = False
    svc.groq_client = groq_mock
    svc.venue_service = None
    svc.orchestrator = None

    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "Toronto, Mar 15-17, moderate"},
    ]
    _, text, phase, _, _ = await svc._intake_turn(messages)

    assert phase == "confirmed"
    assert _CONFIRMATION_MARKER.lower() in text.lower()


@pytest.mark.asyncio
async def test_user_confirming_triggers_itinerary():
    """When user says 'yes' after confirmation question, itinerary generates."""
    from services.conversation_service import ConversationService, _CONFIRMATION_MARKER

    # Last assistant message has the marker
    messages = [
        {"role": "system", "content": "system"},
        {"role": "assistant", "content": "Hey there! Where are you visiting?"},
        {"role": "user", "content": "Toronto March 15-17 moderate"},
        {"role": "assistant", "content": f"Great! Want me to generate your itinerary for Toronto?"},
    ]

    assert ConversationService._user_is_confirming(messages, "yes")
    assert ConversationService._user_is_confirming(messages, "yes please")
    assert ConversationService._user_is_confirming(messages, "go ahead")
    assert not ConversationService._user_is_confirming(messages, "no thanks")


# ---------------------------------------------------------------------------
# Full turn() flow test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_turn_flow():
    """Simulate greeting → intake → confirmed phases using mocked LLM."""
    from services.conversation_service import ConversationService

    # Mock the venue service to avoid DB calls
    venue_mock = MagicMock()
    venue_mock.get_all_venues_for_city = MagicMock(return_value=[
        {"place_key": "cn_tower", "name": "CN Tower", "category": "tourism",
         "address": "Toronto", "description": "Iconic tower", "url": "https://cntower.ca"}
    ])

    # 3 LLM calls: after city, after dates, after pace
    groq_mock = _make_groq_mock([
        "Great! Toronto sounds wonderful. When are you planning to visit?",
        "March 15-17 it is! How would you like to pace your days - relaxed, moderate, or packed?",
        "Perfect! Want me to generate your itinerary for Toronto?",
    ])

    svc = ConversationService.__new__(ConversationService)
    svc.use_groq = True
    svc.use_gemini = False
    svc.groq_client = groq_mock
    svc.venue_service = venue_mock
    svc.orchestrator = None

    # Turn 1: greeting (no user input)
    msgs, text, phase, _, _ = await svc.turn([], user_input=None)
    assert phase == "greeting"

    # Turn 2: user mentions city
    msgs, text, phase, _, _ = await svc.turn(msgs, user_input="I want to visit Toronto")
    assert phase == "intake"

    # Turn 3: user gives dates
    msgs, text, phase, _, _ = await svc.turn(msgs, user_input="March 15-17")
    assert phase == "intake"

    # Turn 4: user gives pace
    msgs, text, phase, _, _ = await svc.turn(msgs, user_input="moderate pace")
    assert phase == "confirmed"

    # Turn 5: user confirms
    # Need to mock the itinerary generation path
    with patch.object(svc, '_generate_grounded_itinerary') as mock_gen:
        mock_gen.return_value = (
            msgs + [{"role": "assistant", "content": "Day 1\nMorning: CN Tower"}],
            "Day 1\nMorning: CN Tower",
            "itinerary",
            None,
            None,
        )
        msgs, text, phase, _, _ = await svc.turn(msgs, user_input="yes")
    assert phase == "itinerary"
    assert "Day 1" in text
