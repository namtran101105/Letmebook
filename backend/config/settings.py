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
    GROQ_MODEL: str = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')
    GROQ_API_BASE_URL: str = 'https://api.groq.com/openai/v1'

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

    @classmethod
    def validate(cls) -> bool:
        """Validate that required settings are configured."""
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable is required")

        # Create data directories if they don't exist
        cls.TRIPS_DIR.mkdir(parents=True, exist_ok=True)
        cls.ITINERARIES_DIR.mkdir(parents=True, exist_ok=True)

        return True


# Create a singleton instance
settings = Settings()
