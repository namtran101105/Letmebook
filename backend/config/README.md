# Config Module - Human Documentation

## Overview

The `config/` module provides centralized configuration management for the MonVoyage backend. It loads environment variables, validates required settings, and exposes configuration values to all other modules.

**Current Status**: Phase 1 - Structure defined, implementation pending  
**Dependencies**: `python-dotenv`, `os`, `typing`

---

## Purpose

- Load environment variables from `.env` file
- Validate required configuration at application startup
- Provide type-safe access to configuration values
- Manage API credentials securely
- Define application constants from MVP requirements

---

## Files

### `settings.py`

Central configuration singleton that all modules import.

**Key Classes**:
- `Settings` - Main configuration class with all settings as class attributes
- `validate()` - Validates required fields and value ranges

**Example Usage**:
```python
from backend.config.settings import settings

# Access configuration
api_key = settings.GROQ_API_KEY
model = settings.GROQ_MODEL
min_budget = settings.MIN_DAILY_BUDGET

# Validate at startup
errors = settings.validate()
if errors:
    raise ConfigurationError(f"Invalid configuration: {errors}")
```

---

## Configuration Categories

### API Credentials

**Groq API** (Required in Phase 1):
- `GROQ_API_KEY` - API key from https://console.groq.com/keys
- `GROQ_MODEL` - Model name (default: "llama-3.3-70b-versatile")
- `GROQ_TEMPERATURE` - Sampling temperature 0-1 (default: 0.2)
- `GROQ_MAX_TOKENS` - Max tokens in response (default: 2048)
- `GROQ_TIMEOUT` - Request timeout in seconds (default: 30)

**MongoDB** (Required in Phase 2):
- `MONGODB_URI` - Connection string (e.g., "mongodb://localhost:27017")
- `MONGODB_DATABASE` - Database name (default: "monvoyage")
- `MONGODB_TIMEOUT` - Connection timeout in ms (default: 5000)

**Google Maps API** (Required in Phase 2):
- `GOOGLE_MAPS_API_KEY` - API key for geocoding and routing

**Weather API** (Required in Phase 2):
- `WEATHER_API_KEY` - API key for weather forecasts
- `WEATHER_API_BASE_URL` - API base URL

### Application Settings

**Server**:
- `HOST` - Server host (default: "127.0.0.1")
- `PORT` - Server port (default: 8000)
- `DEBUG` - Debug mode (default: True)
- `ENVIRONMENT` - Environment name: development|staging|production

**Logging**:
- `LOG_LEVEL` - Logging level: DEBUG|INFO|WARNING|ERROR|CRITICAL
- `LOG_FORMAT` - Log format: json|text (default: "json")

### Application Constants

These values are derived from MVP requirements and should not be changed without consulting `CLAUDE_EMBEDDED.md`:

- `MIN_DAILY_BUDGET = 50.0` - Minimum daily budget in CAD (non-negotiable)
- `DEFAULT_PACE = "moderate"` - Default pace when user doesn't specify
- `MAX_TRIP_DURATION_DAYS = 14` - Maximum trip duration for MVP

---

## Environment Variable Setup

### 1. Create `.env` File

Copy the example template:
```bash
cp backend/.env.example backend/.env
```

### 2. Add Required Values

Edit `backend/.env`:
```bash
# Groq API Configuration
GROQ_API_KEY=gsk_your_actual_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Flask/FastAPI Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=True

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 3. Validate Configuration

Run diagnostics:
```bash
python backend/diagnose.py
```

This will:
- Load configuration from `.env`
- Validate required fields
- Check API key format
- Report missing or invalid settings

---

## Security Best Practices

### Never Commit Secrets

The `.env` file is in `.gitignore`. **Never** commit:
- API keys
- Database passwords
- Any sensitive credentials

### API Key Redaction

When logging, API keys are automatically redacted:
```python
# Original: gsk_1234567890abcdef
# Logged as: ***...cdef
```

### Environment-Specific Configs

For different environments, use separate `.env` files:
- `.env.development` - Local development
- `.env.staging` - Staging server
- `.env.production` - Production server

(Note: This feature is planned, not yet implemented)

---

## Validation Rules

Configuration is validated at startup. Application will **fail to start** if:

1. **Missing Required Fields**:
   - `GROQ_API_KEY` is empty or not set

2. **Invalid Values**:
   - `GROQ_TEMPERATURE` is not between 0 and 1
   - `PORT` is not between 1 and 65535
   - `LOG_LEVEL` is not a valid logging level

3. **Type Mismatches**:
   - `PORT` is not a valid integer
   - `DEBUG` is not a boolean value
   - `GROQ_TEMPERATURE` is not a valid float

---

## Testing

### Running Tests

```bash
# Test configuration loading
pytest backend/tests/config/test_settings.py -v

# Test with specific environment
ENVIRONMENT=production pytest backend/tests/config/test_settings.py
```

### Test Coverage Requirements

- **Unit Tests**: 95% coverage
- **Validation Tests**: 100% coverage (all validation rules tested)
- **Negative Tests**: All error conditions tested

### Example Test Cases

1. ✅ Load configuration from `.env` file
2. ✅ Use default values when env var not set
3. ✅ Convert string "true" to boolean True
4. ✅ Validate required GROQ_API_KEY
5. ✅ Reject GROQ_TEMPERATURE outside 0-1 range
6. ✅ Redact API keys in logs
7. ✅ Detect production environment
8. ❌ Fail startup with missing API key
9. ❌ Reject invalid PORT value
10. ❌ Reject malformed boolean value

---

## Common Issues

### Issue: "GROQ_API_KEY is required"

**Cause**: `.env` file missing or GROQ_API_KEY not set

**Solution**:
1. Create `backend/.env` from `backend/.env.example`
2. Add your Groq API key from https://console.groq.com/keys
3. Ensure no extra spaces around the value

### Issue: "GROQ_TEMPERATURE must be 0-1"

**Cause**: Invalid temperature value in `.env`

**Solution**:
Set `GROQ_TEMPERATURE` to a value between 0 and 1:
```bash
GROQ_TEMPERATURE=0.2
```

### Issue: "Cannot load .env file"

**Cause**: `.env` file has syntax errors

**Solution**:
- Ensure each line is `KEY=value` format
- No spaces around `=`
- Quote values with spaces: `KEY="value with spaces"`
- No comments on same line as values

---

## Integration with Other Modules

### Imported By

All backend modules import configuration:

```python
# In services/nlp_extraction_service.py
from backend.config.settings import settings

groq_client = GroqClient(
    api_key=settings.GROQ_API_KEY,
    model=settings.GROQ_MODEL,
    temperature=settings.GROQ_TEMPERATURE
)
```

```python
# In models/trip_preferences.py
from backend.config.settings import settings

def validate_budget(daily_budget: float) -> bool:
    return daily_budget >= settings.MIN_DAILY_BUDGET
```

### Application Startup

Configuration is validated in `app.py`:

```python
from backend.config.settings import settings

# Validate configuration
errors = settings.validate()
if errors:
    logger.critical("Configuration errors", extra={"errors": errors})
    sys.exit(1)

logger.info("Configuration loaded", extra={
    "environment": settings.ENVIRONMENT,
    "debug_mode": settings.DEBUG
})
```

---

## Future Enhancements (Phase 2/3)

### Phase 2
- [ ] Add MongoDB configuration
- [ ] Add Google Maps API configuration
- [ ] Add Weather API configuration
- [ ] Implement environment-specific config files
- [ ] Add configuration validation for Phase 2 requirements

### Phase 3
- [ ] Add Apache Airflow configuration
- [ ] Add Redis configuration for caching
- [ ] Implement hot-reload for configuration changes
- [ ] Add CLI argument overrides

---

## API Reference

### `Settings` Class

**Attributes**:
- `HOST: str` - Server host address
- `PORT: int` - Server port number
- `DEBUG: bool` - Debug mode flag
- `ENVIRONMENT: str` - Environment name
- `GROQ_API_KEY: str` - Groq API key (required)
- `GROQ_MODEL: str` - Groq model name
- `GROQ_TEMPERATURE: float` - Sampling temperature (0-1)
- `GROQ_MAX_TOKENS: int` - Max response tokens
- `MIN_DAILY_BUDGET: float` - Minimum daily budget (CAD)
- `DEFAULT_PACE: str` - Default trip pace
- `LOG_LEVEL: str` - Logging level

**Methods**:
- `validate() -> List[str]` - Validate configuration, returns list of errors

### Helper Functions

```python
def is_production() -> bool:
    """Check if running in production environment"""
    return settings.ENVIRONMENT == "production"

def is_development() -> bool:
    """Check if running in development environment"""
    return settings.ENVIRONMENT == "development"

def redact_api_key(key: str) -> str:
    """Redact API key to show only last 4 characters"""
    if not key or len(key) < 8:
        return "***INVALID***"
    return f"***...{key[-4:]}"
```

---

## Contributing

When adding new configuration:

1. **Add to `Settings` class** with type hint and default value
2. **Add to `.env.example`** with dummy value
3. **Add validation** in `validate()` method
4. **Update this README** with description
5. **Add tests** for new configuration
6. **Update CLAUDE.md** with agent instructions

---

**Last Updated**: 2026-02-07  
**Maintained By**: Backend Team  
**Questions**: See `backend/config/CLAUDE.md` for detailed agent instructions
