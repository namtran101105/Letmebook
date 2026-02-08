"""Test confirmation detection logic (Bug A fix verification)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.conversation_service import (
    ConversationService,
    _AFFIRMATIVE_PATTERNS,
    _CONFIRMATION_MARKER,
)


# ---------------------------------------------------------------------------
# Marker consistency test
# ---------------------------------------------------------------------------

def test_confirmation_marker_in_system_prompt():
    """The confirmation marker phrase must appear in the INTAKE_SYSTEM_PROMPT."""
    from services.conversation_service import INTAKE_SYSTEM_PROMPT

    assert _CONFIRMATION_MARKER.lower() in INTAKE_SYSTEM_PROMPT.lower(), (
        f"_CONFIRMATION_MARKER '{_CONFIRMATION_MARKER}' not found in "
        f"INTAKE_SYSTEM_PROMPT — confirmation will never trigger!"
    )


# ---------------------------------------------------------------------------
# Affirmative pattern tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("user_input", [
    "yes", "Yes", "YES", "yes please", "yep", "yeah",
    "sure", "go ahead", "let's do it", "absolutely",
    "ok", "okay", "sounds good", "generate it",
    "please", "of course", "definitely",
])
def test_affirmative_patterns_match(user_input):
    """Common affirmative responses must be recognised."""
    assert _AFFIRMATIVE_PATTERNS.match(user_input.strip()), (
        f"'{user_input}' should be recognised as affirmative"
    )


@pytest.mark.parametrize("user_input", [
    "no", "not yet", "change the dates", "actually I want packed",
    "what about museums?", "tell me more",
])
def test_non_affirmative_not_matched(user_input):
    """Non-affirmative inputs must not be mistaken for confirmation."""
    assert not _AFFIRMATIVE_PATTERNS.match(user_input.strip()), (
        f"'{user_input}' should NOT be recognised as affirmative"
    )


# ---------------------------------------------------------------------------
# _user_is_confirming logic tests (no LLM needed)
# ---------------------------------------------------------------------------

def test_user_confirming_requires_marker_in_last_assistant_msg():
    """Confirmation only triggers when last assistant msg has the marker."""
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "assistant", "content": "What city do you want to visit?"},
        {"role": "user", "content": "Toronto"},
        {"role": "assistant", "content": f"Ready to generate your itinerary for Toronto?"},
        {"role": "user", "content": "yes"},
    ]
    assert ConversationService._user_is_confirming(messages, "yes")


def test_user_confirming_false_without_marker():
    """If last assistant msg lacks the marker, confirmation should not fire."""
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "assistant", "content": "What dates are you visiting?"},
        {"role": "user", "content": "yes"},
    ]
    assert not ConversationService._user_is_confirming(messages, "yes")


def test_user_confirming_false_on_non_affirmative():
    """Non-affirmative user input should not confirm even with marker present."""
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "assistant", "content": "Want me to generate your itinerary?"},
        {"role": "user", "content": "not yet"},
    ]
    assert not ConversationService._user_is_confirming(messages, "not yet")
