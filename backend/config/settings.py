"""
Application configuration and settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings loaded from environment variables."""

    # Groq API Configuration
    GROQ_API_KEY: str = os.getenv('GROQ_API_KEY', '')
    GROQ_MODEL: str = os.getenv('GROQ_MODEL', 'moonshotai/kimi-k2-instruct')
    GROQ_API_BASE_URL: str = 'https://api.groq.com/openai/v1'
    GROQ_TEMPERATURE: float = float(os.getenv('GROQ_TEMPERATURE', '0.2'))
    GROQ_MAX_TOKENS: int = int(os.getenv('GROQ_MAX_TOKENS', '2048'))
    GROQ_TIMEOUT: int = int(os.getenv('GROQ_TIMEOUT', '30'))  # seconds

    # Google Gemini API Configuration (fallback LLM)
    GEMINI_KEY: str = os.getenv('GEMINI_KEY', '')
    GEMINI_MODEL: str = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
    GEMINI_EXTRACTION_TEMPERATURE: float = float(os.getenv('GEMINI_EXTRACTION_TEMPERATURE', '0.2'))
    GEMINI_EXTRACTION_MAX_TOKENS: int = int(os.getenv('GEMINI_EXTRACTION_MAX_TOKENS', '2048'))
    GEMINI_ITINERARY_TEMPERATURE: float = float(os.getenv('GEMINI_ITINERARY_TEMPERATURE', '0.7'))
    GEMINI_ITINERARY_MAX_TOKENS: int = int(os.getenv('GEMINI_ITINERARY_MAX_TOKENS', '4096'))
    GEMINI_TIMEOUT: int = int(os.getenv('GEMINI_TIMEOUT', '30'))  # seconds
    GEMINI_MAX_RETRIES: int = int(os.getenv('GEMINI_MAX_RETRIES', '2'))  # Reduced from 3 to 2

    # Google Maps API Configuration
    GOOGLE_MAPS_API_KEY: str = os.getenv('GOOGLE_MAPS_API_KEY', '')

    # Application Configuration
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    PORT: int = int(os.getenv('PORT', '5000'))
    HOST: str = os.getenv('HOST', '0.0.0.0')

    # Data Storage
    DATA_DIR: Path = Path(__file__).parent.parent.parent / 'data'
    TRIPS_DIR: Path = DATA_DIR / 'trips'
    ITINERARIES_DIR: Path = DATA_DIR / 'itineraries'

    # NLP Extraction Settings
    EXTRACTION_TEMPERATURE: float = float(os.getenv('EXTRACTION_TEMPERATURE', '0.2'))
    EXTRACTION_MAX_TOKENS: int = int(os.getenv('EXTRACTION_MAX_TOKENS', '2048'))

    # Itinerary Generation Settings
    ITINERARY_TEMPERATURE: float = float(os.getenv('ITINERARY_TEMPERATURE', '0.7'))
    ITINERARY_MAX_TOKENS: int = int(os.getenv('ITINERARY_MAX_TOKENS', '4096'))

    # Valid pace values
    VALID_PACES = {"relaxed", "moderate", "packed"}

    # Pace parameters for itinerary generation
    PACE_PARAMS = {
        "relaxed": {
            "activities_per_day": 2,
            "minutes_per_activity": (90, 120),
            "buffer_between_activities": 20,
            "lunch_duration": 90,
            "dinner_duration": 120,
        },
        "moderate": {
            "activities_per_day": 3,
            "minutes_per_activity": (60, 90),
            "buffer_between_activities": 15,
            "lunch_duration": 60,
            "dinner_duration": 90,
        },
        "packed": {
            "activities_per_day": 4,
            "minutes_per_activity": (30, 60),
            "buffer_between_activities": 5,
            "lunch_duration": 45,
            "dinner_duration": 60,
        },
    }

    @classmethod
    def validate(cls) -> bool:
        """Validate that required settings are configured."""
        if not cls.GROQ_API_KEY and not cls.GEMINI_KEY:
            raise ValueError("At least one of GROQ_API_KEY or GEMINI_KEY must be set in .env")

        # Create data directories if they don't exist
        cls.TRIPS_DIR.mkdir(parents=True, exist_ok=True)
        cls.ITINERARIES_DIR.mkdir(parents=True, exist_ok=True)

        return True


# Create a singleton instance
settings = Settings()
