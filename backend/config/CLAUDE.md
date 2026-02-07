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
4. Manage API credentials (Groq, Google Maps, Weather API)
5. Define application constants (timeouts, retries, defaults)

### Planned (Phase 2/3)
6. MongoDB connection configuration
7. Apache Airflow configuration
8. Redis configuration (for caching)
9. Environment-specific configs (dev/staging/prod)

---

## Files in This Module

### `settings.py`
**Purpose**: Central configuration singleton that loads and validates environment variables.

**Must Provide**:
```python
class Settings:
    # Flask/FastAPI Configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    ENVIRONMENT: str = "development"  # development|staging|production
    
    # Groq API Configuration
    GROQ_API_KEY: str  # REQUIRED
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
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json|text
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate required configuration. Returns list of missing/invalid fields."""
        errors = []
        if not cls.GROQ_API_KEY:
            errors.append("GROQ_API_KEY is required")
        if cls.GROQ_TEMPERATURE < 0 or cls.GROQ_TEMPERATURE > 1:
            errors.append("GROQ_TEMPERATURE must be between 0 and 1")
        # Add more validation...
        return errors
```

**Configuration Loading Priority**:
1. Environment variables (highest priority)
2. `.env` file in backend directory
3. Default values in `settings.py` (lowest priority)

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
- **WARNING**: Using default values, optional config missing
- **ERROR**: Required configuration missing, invalid values
- **CRITICAL**: Cannot start application due to config errors

### Log Examples
```python
logger.info("Configuration loaded successfully", extra={
    "environment": Settings.ENVIRONMENT,
    "debug_mode": Settings.DEBUG,
    "groq_model": Settings.GROQ_MODEL
})

logger.warning("Google Maps API key not configured, geocoding disabled", extra={
    "feature": "geocoding",
    "impact": "Starting location must be coordinates"
})

logger.error("Required configuration missing", extra={
    "missing_fields": ["GROQ_API_KEY", "MONGODB_URI"],
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

logger.info("Groq API configured", extra={
    "api_key": redact_api_key(Settings.GROQ_API_KEY),
    "model": Settings.GROQ_MODEL
})
```

---

## Testing Strategy

### Unit Tests Required
1. Test environment variable loading from `.env` file
2. Test default value fallback when env var not set
3. Test type coercion (string "true" → boolean True)
4. Test validation of required fields
5. Test validation of value ranges (temperature 0-1)
6. Test API key redaction in logs
7. Test configuration singleton pattern (same instance across imports)

### Integration Tests Required
1. Test configuration with missing `.env` file (should use defaults)
2. Test configuration with invalid `.env` format
3. Test configuration in different environments (dev/staging/prod)

### Negative Tests Required
1. Test startup failure with missing required config
2. Test invalid GROQ_TEMPERATURE (negative or > 1)
3. Test invalid PORT (non-numeric string)
4. Test empty API key
5. Test malformed MongoDB URI (Phase 2)

### Test Examples
```python
def test_groq_api_key_required():
    """Test that missing GROQ_API_KEY raises error"""
    with mock.patch.dict(os.environ, {}, clear=True):
        errors = Settings.validate()
        assert "GROQ_API_KEY is required" in errors

def test_default_temperature():
    """Test that GROQ_TEMPERATURE defaults to 0.2"""
    settings = Settings()
    assert settings.GROQ_TEMPERATURE == 0.2

def test_api_key_redaction():
    """Test that API keys are redacted in logs"""
    key = "sk_test_1234567890abcdef"
    redacted = redact_api_key(key)
    assert redacted == "***...cdef"
    assert "1234567890" not in redacted

def test_invalid_temperature_range():
    """Test that GROQ_TEMPERATURE outside 0-1 is rejected"""
    with mock.patch.dict(os.environ, {"GROQ_TEMPERATURE": "1.5"}):
        errors = Settings.validate()
        assert any("GROQ_TEMPERATURE" in err for err in errors)

def test_production_environment_detection():
    """Test production mode detection"""
    with mock.patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        settings = Settings()
        assert is_production() == True
        assert is_development() == False
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
- `clients/groq_client.py` - Needs GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE
- `services/nlp_extraction_service.py` - Needs extraction settings
- `app.py` - Needs HOST, PORT, DEBUG, LOG_LEVEL
- `models/trip_preferences.py` - Needs MIN_DAILY_BUDGET, DEFAULT_PACE
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
from typing import List, Optional
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
    
    # Groq API Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_TEMPERATURE: float = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
    GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "2048"))
    GROQ_TIMEOUT: int = int(os.getenv("GROQ_TIMEOUT", "30"))
    
    # Application Constants (from MVP requirements)
    MIN_DAILY_BUDGET: float = 50.0  # Non-negotiable from CLAUDE_EMBEDDED.md
    DEFAULT_PACE: str = "moderate"
    MAX_TRIP_DURATION_DAYS: int = 14
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate required configuration"""
        errors = []
        
        # Required fields
        if not cls.GROQ_API_KEY:
            errors.append("GROQ_API_KEY is required")
        
        # Range validation
        if not 0 <= cls.GROQ_TEMPERATURE <= 1:
            errors.append(f"GROQ_TEMPERATURE must be 0-1, got {cls.GROQ_TEMPERATURE}")
        
        if not 1 <= cls.PORT <= 65535:
            errors.append(f"PORT must be 1-65535, got {cls.PORT}")
        
        return errors

# Singleton instance
settings = Settings()
```

---

## Assumptions
1. `.env` file is in `backend/` directory (same level as `app.py`)
2. All API keys are string values
3. Boolean environment variables use "true"/"false" (case-insensitive)
4. Numeric environment variables are valid integers/floats

## Open Questions
1. Should we support `.env.development`, `.env.staging`, `.env.production` files?
2. Do we need runtime configuration reloading (hot reload)?
3. Should configuration be validated at import time or application startup?
4. Do we need configuration override via CLI arguments?

---

**Last Updated**: 2026-02-07  
**Status**: Phase 1 - Documentation Complete, Implementation Pending
