"""Test pace → exact activity count mapping (Bug 1.2 fix verification)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


def test_pace_activity_counts():
    """relaxed=2, moderate=3, packed=4 — exact counts required."""
    from config.settings import settings

    expected = {"relaxed": 2, "moderate": 3, "packed": 4}
    for pace, count in expected.items():
        actual = settings.PACE_PARAMS[pace]["activities_per_day"]
        assert actual == count, (
            f"Pace '{pace}': expected {count} activities/day, got {actual}"
        )


def test_all_paces_present():
    """All three paces must be configured."""
    from config.settings import settings

    for pace in ("relaxed", "moderate", "packed"):
        assert pace in settings.PACE_PARAMS, f"Missing pace config: {pace}"
        assert "activities_per_day" in settings.PACE_PARAMS[pace]


def test_pace_params_complete():
    """Each pace must have all required timing fields."""
    from config.settings import settings

    required_keys = [
        "activities_per_day", "minutes_per_activity",
        "buffer_between_activities", "lunch_duration", "dinner_duration",
    ]
    for pace in ("relaxed", "moderate", "packed"):
        for key in required_keys:
            assert key in settings.PACE_PARAMS[pace], (
                f"Pace '{pace}' missing key: {key}"
            )
