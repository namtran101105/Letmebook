# Config Module - Agent Instructions

**Parent Contexts**:
- `MONVOYAGE/CLAUDE.md` (project-wide architecture, testing conventions)
- `MONVOYAGE/backend/CLAUDE_EMBEDDED.md` (backend-operational rules, MVP requirements)

**Module Purpose**: Centralized configuration management for all backend services, including environment variables, API credentials, and runtime settings.

---

## Module Responsibilities

### Current (Phase 1)
1. Load environment variables from `.env` file
2. Provide configuration values to other modules via `settings.py`
3. Validate required configuration at startup
4. Manage API credentials (Gemini, Groq, Google Maps, Weather API)
5. Define application constants (timeouts, retries, defaults)
6. Define pace parameters and valid interests/paces for itinerary generation

### Planned (Phase 2/3)
7. MongoDB connection configuration
8. Apache Airflow configuration
9. Redis configuration (for caching)
10. Environment-specific configs (dev/staging/prod)

---

## Files in This Module

### `settings.py`
**Purpose**: Central configuration singleton that loads and validates environment variables. All LLM and application configuration lives here (there is no separate `gemini.py` file).

**Must Provide**:
```python
class Settings:
    # Flask/FastAPI Configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    ENVIRONMENT: str = "development"  # development|staging|production

    # Gemini API Configuration (PRIMARY LLM)
    GEMINI_KEY: str  # REQUIRED - env var GEMINI_KEY
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_EXTRACTION_TEMPERATURE: float = 0.2
    GEMINI_ITINERARY_TEMPERATURE: float = 0.7
    GEMINI_EXTRACTION_MAX_TOKENS: int = 2048
    GEMINI_ITINERARY_MAX_TOKENS: int = 8192

    # Groq API Configuration (FALLBACK LLM)
    GROQ_API_KEY: str  # OPTIONAL - fallback when Gemini unavailable
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.2
    GROQ_MAX_TOKENS: int = 2048
    GROQ_TIMEOUT: int = 30  # seconds

    # MongoDB Configuration (Phase 2)
    MONGODB_URI: str  # REQUIRED in Phase 2
    MONGODB_DATABASE: str = "monvoyage"
    MONGODB_TIMEOUT: int = 5000  # milliseconds

    # Google Maps API (Phase 2)
    GOOGLE_MAPS_API_KEY: str  # REQUIRED in Phase 2

    # Weather API (Phase 2)
    WEATHER_API_KEY: str  # REQUIRED in Phase 2
    WEATHER_API_BASE_URL: str

    # Airflow Configuration (Phase 3)
    AIRFLOW_WEBSERVER_URL: str
    AIRFLOW_USERNAME: str
    AIRFLOW_PASSWORD: str

    # Application Constants
    MIN_DAILY_BUDGET: float = 50.0  # CAD
    DEFAULT_PACE: str = "moderate"
    MAX_TRIP_DURATION_DAYS: int = 14

    # Pace Parameters (from MVP spec)
    PACE_PARAMS: Dict = {
        "relaxed": {
            "activities_per_day": (2, 3),
            "minutes_per_activity": (90, 120),
            "buffer_minutes": 20,
            "lunch_minutes": 90,
            "dinner_minutes": 120
        },
        "moderate": {
            "activities_per_day": (4, 5),
            "minutes_per_activity": (60, 90),
            "buffer_minutes": 15,
            "lunch_minutes": 75,
            "dinner_minutes": 90
        },
        "packed": {
            "activities_per_day": (6, 8),
            "minutes_per_activity": (30, 60),
            "buffer_minutes": 5,
            "lunch_minutes": 45,
            "dinner_minutes": 60
        }
    }

    VALID_PACES: List[str] = ["relaxed", "moderate", "packed"]

    VALID_INTERESTS: List[str] = [
        "history", "food", "waterfront", "nature",
        "arts", "museums", "shopping", "nightlife"
    ]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json|text

    @classmethod
    def validate(cls) -> List[str]:
        """Validate required configuration. Returns list of missing/invalid fields."""
        errors = []
        if not cls.GEMINI_KEY:
            errors.append("GEMINI_KEY is required")
        if cls.GEMINI_EXTRACTION_TEMPERATURE < 0 or cls.GEMINI_EXTRACTION_TEMPERATURE > 1:
            errors.append("GEMINI_EXTRACTION_TEMPERATURE must be between 0 and 1")
        if cls.GEMINI_ITINERARY_TEMPERATURE < 0 or cls.GEMINI_ITINERARY_TEMPERATURE > 1:
            errors.append("GEMINI_ITINERARY_TEMPERATURE must be between 0 and 1")
        if cls.GROQ_API_KEY and (cls.GROQ_TEMPERATURE < 0 or cls.GROQ_TEMPERATURE > 1):
            errors.append("GROQ_TEMPERATURE must be between 0 and 1")
        # Add more validation...
        return errors
```

**Configuration Loading Priority**:
1. Environment variables (highest priority)
2. `.env` file in backend directory
3. Default values in `settings.py` (lowest priority)

**Important**: There is NO separate `gemini.py` configuration file. All Gemini and Groq configuration is consolidated in `settings.py`.

---

## Non-Negotiable Rules

### Security
1. **NEVER** commit `.env` files or API keys to version control
2. **ALWAYS** use `.env.example` as template (with dummy values)
3. **REDACT** API keys in logs (show only last 4 characters)
4. **ROTATE** API keys if accidentally exposed

### Validation
1. **FAIL FAST**: Validate all required config at application startup
2. **EXPLICIT ERRORS**: Provide clear error messages for missing/invalid config
3. **TYPE CHECKING**: Validate data types (int, float, bool) at load time

### Environment Detection
```python
def is_production() -> bool:
    return Settings.ENVIRONMENT == "production"

def is_development() -> bool:
    return Settings.ENVIRONMENT == "development"
```

---

## Logging Requirements

### What to Log
- **INFO**: Configuration loaded successfully, environment detected
- **WARNING**: Using default values, optional config missing, Groq fallback active
- **ERROR**: Required configuration missing, invalid values
- **CRITICAL**: Cannot start application due to config errors

### Log Examples
```python
logger.info("Configuration loaded successfully", extra={
    "environment": Settings.ENVIRONMENT,
    "debug_mode": Settings.DEBUG,
    "primary_llm": "Gemini",
    "gemini_model": Settings.GEMINI_MODEL,
    "groq_fallback_available": bool(Settings.GROQ_API_KEY)
})

logger.warning("Groq API key not configured, fallback LLM disabled", extra={
    "feature": "llm_fallback",
    "impact": "No fallback if Gemini fails"
})

logger.error("Required configuration missing", extra={
    "missing_fields": ["GEMINI_KEY"],
    "action": "Application cannot start"
})
```

### Secrets Redaction
```python
def redact_api_key(key: str) -> str:
    """Redact API key to show only last 4 characters"""
    if not key or len(key) < 8:
        return "***INVALID***"
    return f"***...{key[-4:]}"

logger.info("Gemini API configured", extra={
    "api_key": redact_api_key(Settings.GEMINI_KEY),
    "model": Settings.GEMINI_MODEL
})
```

---

## Testing Strategy

### Unit Tests Required
1. Test environment variable loading from `.env` file
2. Test default value fallback when env var not set
3. Test type coercion (string "true" -> boolean True)
4. Test validation of required fields (GEMINI_KEY)
5. Test validation of value ranges (temperatures 0-1)
6. Test API key redaction in logs
7. Test configuration singleton pattern (same instance across imports)
8. Test PACE_PARAMS structure and VALID_PACES list
9. Test VALID_INTERESTS list contents

### Integration Tests Required
1. Test configuration with missing `.env` file (should use defaults)
2. Test configuration with invalid `.env` format
3. Test configuration in different environments (dev/staging/prod)

### Negative Tests Required
1. Test startup failure with missing required config (GEMINI_KEY)
2. Test invalid GEMINI_EXTRACTION_TEMPERATURE (negative or > 1)
3. Test invalid GEMINI_ITINERARY_TEMPERATURE (negative or > 1)
4. Test invalid PORT (non-numeric string)
5. Test empty API key
6. Test malformed MongoDB URI (Phase 2)

### Test Examples
```python
def test_gemini_key_required():
    """Test that missing GEMINI_KEY raises error"""
    with mock.patch.dict(os.environ, {}, clear=True):
        errors = Settings.validate()
        assert "GEMINI_KEY is required" in errors

def test_default_extraction_temperature():
    """Test that GEMINI_EXTRACTION_TEMPERATURE defaults to 0.2"""
    settings = Settings()
    assert settings.GEMINI_EXTRACTION_TEMPERATURE == 0.2

def test_default_itinerary_temperature():
    """Test that GEMINI_ITINERARY_TEMPERATURE defaults to 0.7"""
    settings = Settings()
    assert settings.GEMINI_ITINERARY_TEMPERATURE == 0.7

def test_api_key_redaction():
    """Test that API keys are redacted in logs"""
    key = "AIzaSyA1234567890abcdef"
    redacted = redact_api_key(key)
    assert redacted == "***...cdef"
    assert "1234567890" not in redacted

def test_invalid_temperature_range():
    """Test that temperatures outside 0-1 are rejected"""
    with mock.patch.dict(os.environ, {"GEMINI_EXTRACTION_TEMPERATURE": "1.5"}):
        errors = Settings.validate()
        assert any("GEMINI_EXTRACTION_TEMPERATURE" in err for err in errors)

def test_production_environment_detection():
    """Test production mode detection"""
    with mock.patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        settings = Settings()
        assert is_production() == True
        assert is_development() == False

def test_pace_params_structure():
    """Test PACE_PARAMS has all required paces"""
    settings = Settings()
    for pace in settings.VALID_PACES:
        assert pace in settings.PACE_PARAMS
        assert "activities_per_day" in settings.PACE_PARAMS[pace]
```

---

## Error Handling

### Configuration Load Errors
```python
class ConfigurationError(Exception):
    """Raised when configuration is missing or invalid"""
    def __init__(self, message: str, missing_fields: List[str] = None):
        self.message = message
        self.missing_fields = missing_fields or []
        super().__init__(self.message)

# Usage in settings.py
def load_settings() -> Settings:
    settings = Settings()
    errors = settings.validate()
    if errors:
        logger.critical("Configuration validation failed", extra={
            "errors": errors
        })
        raise ConfigurationError(
            "Application cannot start due to configuration errors",
            missing_fields=errors
        )
    return settings
```

---

## Integration Points

### Used By
- `clients/gemini_client.py` - Needs GEMINI_KEY, GEMINI_MODEL, GEMINI_EXTRACTION_TEMPERATURE, GEMINI_ITINERARY_TEMPERATURE, GEMINI_EXTRACTION_MAX_TOKENS, GEMINI_ITINERARY_MAX_TOKENS
- `clients/groq_client.py` - Needs GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE (fallback)
- `services/nlp_extraction_service.py` - Needs extraction settings
- `services/itinerary_service.py` - Needs itinerary generation settings, PACE_PARAMS
- `app.py` - Needs HOST, PORT, DEBUG, LOG_LEVEL
- `models/trip_preferences.py` - Needs MIN_DAILY_BUDGET, DEFAULT_PACE, VALID_PACES, VALID_INTERESTS
- (Phase 2) All modules needing MongoDB connection
- (Phase 2) All modules needing Google Maps API
- (Phase 3) Airflow DAGs needing scraping configuration

### Dependencies
- `python-dotenv` - Load `.env` files
- `os` - Access environment variables
- `typing` - Type hints

---

## File Structure Example

```python
# backend/config/settings.py
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings:
    """Centralized configuration management"""

    # Flask/FastAPI Configuration
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Gemini API Configuration (PRIMARY LLM)
    GEMINI_KEY: str = os.getenv("GEMINI_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_EXTRACTION_TEMPERATURE: float = float(os.getenv("GEMINI_EXTRACTION_TEMPERATURE", "0.2"))
    GEMINI_ITINERARY_TEMPERATURE: float = float(os.getenv("GEMINI_ITINERARY_TEMPERATURE", "0.7"))
    GEMINI_EXTRACTION_MAX_TOKENS: int = int(os.getenv("GEMINI_EXTRACTION_MAX_TOKENS", "2048"))
    GEMINI_ITINERARY_MAX_TOKENS: int = int(os.getenv("GEMINI_ITINERARY_MAX_TOKENS", "8192"))

    # Groq API Configuration (FALLBACK LLM)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_TEMPERATURE: float = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
    GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "2048"))
    GROQ_TIMEOUT: int = int(os.getenv("GROQ_TIMEOUT", "30"))

    # Application Constants (from MVP requirements)
    MIN_DAILY_BUDGET: float = 50.0  # Non-negotiable from CLAUDE_EMBEDDED.md
    DEFAULT_PACE: str = "moderate"
    MAX_TRIP_DURATION_DAYS: int = 14

    # Pace Parameters
    PACE_PARAMS: Dict = {
        "relaxed": {
            "activities_per_day": (2, 3),
            "minutes_per_activity": (90, 120),
            "buffer_minutes": 20,
            "lunch_minutes": 90,
            "dinner_minutes": 120
        },
        "moderate": {
            "activities_per_day": (4, 5),
            "minutes_per_activity": (60, 90),
            "buffer_minutes": 15,
            "lunch_minutes": 75,
            "dinner_minutes": 90
        },
        "packed": {
            "activities_per_day": (6, 8),
            "minutes_per_activity": (30, 60),
            "buffer_minutes": 5,
            "lunch_minutes": 45,
            "dinner_minutes": 60
        }
    }

    VALID_PACES: List[str] = ["relaxed", "moderate", "packed"]

    VALID_INTERESTS: List[str] = [
        "history", "food", "waterfront", "nature",
        "arts", "museums", "shopping", "nightlife"
    ]

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    @classmethod
    def validate(cls) -> List[str]:
        """Validate required configuration"""
        errors = []

        # Required fields
        if not cls.GEMINI_KEY:
            errors.append("GEMINI_KEY is required")

        # Range validation
        if not 0 <= cls.GEMINI_EXTRACTION_TEMPERATURE <= 1:
            errors.append(f"GEMINI_EXTRACTION_TEMPERATURE must be 0-1, got {cls.GEMINI_EXTRACTION_TEMPERATURE}")

        if not 0 <= cls.GEMINI_ITINERARY_TEMPERATURE <= 1:
            errors.append(f"GEMINI_ITINERARY_TEMPERATURE must be 0-1, got {cls.GEMINI_ITINERARY_TEMPERATURE}")

        if cls.GROQ_API_KEY and not 0 <= cls.GROQ_TEMPERATURE <= 1:
            errors.append(f"GROQ_TEMPERATURE must be 0-1, got {cls.GROQ_TEMPERATURE}")

        if not 1 <= cls.PORT <= 65535:
            errors.append(f"PORT must be 1-65535, got {cls.PORT}")

        return errors

# Singleton instance
settings = Settings()
```

---

## Environment Variables

### Required
```bash
# Gemini API Configuration (PRIMARY LLM)
GEMINI_KEY=your_gemini_api_key_here
```

### Optional (with defaults)
```bash
# Gemini model settings
GEMINI_MODEL=gemini-2.0-flash
GEMINI_EXTRACTION_TEMPERATURE=0.2
GEMINI_ITINERARY_TEMPERATURE=0.7
GEMINI_EXTRACTION_MAX_TOKENS=2048
GEMINI_ITINERARY_MAX_TOKENS=8192

# Groq API Configuration (FALLBACK LLM)
GROQ_API_KEY=gsk_your_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=0.2
GROQ_MAX_TOKENS=2048

# Flask/FastAPI Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=True

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Assumptions
1. `.env` file is in `backend/` directory (same level as `app.py`)
2. All API keys are string values
3. Boolean environment variables use "true"/"false" (case-insensitive)
4. Numeric environment variables are valid integers/floats
5. Gemini is always available as primary LLM; Groq is optional fallback

## Open Questions
1. Should we support `.env.development`, `.env.staging`, `.env.production` files?
2. Do we need runtime configuration reloading (hot reload)?
3. Should configuration be validated at import time or application startup?
4. Do we need configuration override via CLI arguments?

---

**Last Updated**: 2026-02-07
**Status**: Phase 1 - Gemini primary LLM, Groq fallback, settings.py consolidated
