"""
Centralized configuration management for MonVoyage backend.

Loads environment variables from .env file and provides typed settings
to all backend modules. Includes validation for required configuration.

Usage:
    from config.settings import settings
    api_key = settings.GEMINI_KEY
"""

import os
import logging
from typing import List
from pathlib import Path

from dotenv import load_dotenv

# Load .env from backend directory
_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env")

logger = logging.getLogger(__name__)


class Settings:
    """Centralized configuration singleton for all backend services."""

    # ===== FastAPI Configuration =====
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # ===== Gemini API Configuration (Primary LLM) =====
    GEMINI_KEY: str = os.getenv("GEMINI_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    GEMINI_EXTRACTION_TEMPERATURE: float = float(
        os.getenv("EXTRACTION_TEMPERATURE", "0.2")
    )
    GEMINI_ITINERARY_TEMPERATURE: float = float(
        os.getenv("ITINERARY_TEMPERATURE", "0.7")
    )
    GEMINI_EXTRACTION_MAX_TOKENS: int = int(
        os.getenv("EXTRACTION_MAX_TOKENS", "2048")
    )
    GEMINI_ITINERARY_MAX_TOKENS: int = int(
        os.getenv("ITINERARY_MAX_TOKENS", "8192")
    )
    GEMINI_TIMEOUT: int = int(os.getenv("GEMINI_TIMEOUT", "60"))

    # ===== Groq API Configuration (Alternative/Fallback LLM) =====
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_TEMPERATURE: float = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
    GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "2048"))
    GROQ_TIMEOUT: int = int(os.getenv("GROQ_TIMEOUT", "30"))

    # ===== Airflow / Venue Database =====
    APP_DB_URL: str = os.getenv(
        "APP_DB_URL",
        "postgresql+psycopg2://app:app@localhost:5432/app",
    )

    # ===== Application Constants (Non-Negotiable MVP Rules) =====
    MIN_DAILY_BUDGET: float = 50.0  # CAD — minimum $50/day for meals + activities
    DEFAULT_PACE: str = "moderate"
    MAX_TRIP_DURATION_DAYS: int = 14
    DEFAULT_CITY: str = os.getenv("DEFAULT_CITY", "Toronto")
    DEFAULT_COUNTRY: str = os.getenv("DEFAULT_COUNTRY", "Canada")
    VALID_PACES: List[str] = ["relaxed", "moderate", "packed"]
    VALID_INTERESTS: List[str] = [
        "history", "food", "waterfront", "nature",
        "arts", "museums", "shopping", "nightlife",
    ]
    VALID_TRANSPORTATION_MODES: List[str] = [
        "own car", "rental car", "public transit", "walking only", "mixed",
    ]

    # ===== Pace-Specific Parameters (from CLAUDE_EMBEDDED.md) =====
    PACE_PARAMS = {
        "relaxed": {
            "activities_per_day": (2, 3),
            "minutes_per_activity": (90, 120),
            "buffer_between_activities": 20,
            "lunch_duration": 90,
            "dinner_duration": 120,
        },
        "moderate": {
            "activities_per_day": (4, 5),
            "minutes_per_activity": (60, 90),
            "buffer_between_activities": 15,
            "lunch_duration": 60,
            "dinner_duration": 90,
        },
        "packed": {
            "activities_per_day": (6, 8),
            "minutes_per_activity": (30, 60),
            "buffer_between_activities": 5,
            "lunch_duration": 45,
            "dinner_duration": 60,
        },
    }

    # ===== Logging =====
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    @classmethod
    def validate(cls) -> List[str]:
        """Validate required configuration. Returns list of errors (empty = valid)."""
        errors = []

        if not cls.GEMINI_KEY and not cls.GROQ_API_KEY:
            errors.append(
                "At least one of GEMINI_KEY or GROQ_API_KEY is required — "
                "set it in backend/.env"
            )

        if not 0 <= cls.GEMINI_EXTRACTION_TEMPERATURE <= 2:
            errors.append(
                f"EXTRACTION_TEMPERATURE must be 0-2, got {cls.GEMINI_EXTRACTION_TEMPERATURE}"
            )

        if not 0 <= cls.GEMINI_ITINERARY_TEMPERATURE <= 2:
            errors.append(
                f"ITINERARY_TEMPERATURE must be 0-2, got {cls.GEMINI_ITINERARY_TEMPERATURE}"
            )

        if not 1 <= cls.PORT <= 65535:
            errors.append(f"PORT must be 1-65535, got {cls.PORT}")

        return errors


def redact_api_key(key: str) -> str:
    """Redact API key to show only last 4 characters."""
    if not key or len(key) < 8:
        return "***INVALID***"
    return f"***...{key[-4:]}"


# Singleton instance — import this everywhere
settings = Settings()
