# Utils Module - Agent Instructions

**Parent Contexts**:
- `MONVOYAGE/CLAUDE.md` (project-wide architecture, testing conventions)
- `MONVOYAGE/backend/CLAUDE_EMBEDDED.md` (backend-operational rules, MVP requirements)

**Module Purpose**: Utility functions and helper classes used across the backend - ID generation, date parsing, validation helpers, logging configuration, and common operations. Supports both Gemini (primary) and Groq (fallback) LLM workflows.

---

## Module Responsibilities

### Current (Phase 1)
1. **ID Generator** (`id_generator.py`) - Generate unique trip IDs, activity IDs, request IDs
2. UUID utilities
3. Request correlation ID management

### Planned (Phase 2/3)
4. **Date Utilities** (`date_utils.py`) - Parse date strings, validate date ranges, calculate durations
5. **Validation Helpers** (`validation_utils.py`) - Common validation functions
6. **Logging Setup** (`logging_utils.py`) - Structured logging configuration
7. **Cache Utilities** (`cache_utils.py`) - Redis caching helpers
8. **String Utilities** (`string_utils.py`) - Text formatting, sanitization

---

## Files in This Module

### `id_generator.py` (Phase 1 - Current)

**Purpose**: Generate unique identifiers for trips, activities, and requests.

**Must Include**:
```python
import uuid
from typing import Optional
from datetime import datetime

class IDGenerator:
    """Generate unique identifiers with optional prefixes"""
    
    @staticmethod
    def generate_trip_id(prefix: str = "trip") -> str:
        """
        Generate unique trip ID.
        
        Format: trip_<uuid>
        Example: trip_a1b2c3d4-e5f6-7890-abcd-ef1234567890
        
        Args:
            prefix: ID prefix (default: "trip")
        
        Returns:
            Unique trip ID string
        """
        return f"{prefix}_{uuid.uuid4()}"
    
    @staticmethod
    def generate_activity_id(prefix: str = "activity") -> str:
        """
        Generate unique activity ID.
        
        Format: activity_<uuid>
        Example: activity_12345678-90ab-cdef-1234-567890abcdef
        """
        return f"{prefix}_{uuid.uuid4()}"
    
    @staticmethod
    def generate_request_id(prefix: str = "req") -> str:
        """
        Generate unique request ID for correlation logging.
        
        Format: req_<timestamp>_<short-uuid>
        Example: req_20260207_a1b2c3d4
        
        Args:
            prefix: ID prefix (default: "req")
        
        Returns:
            Unique request ID string
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"{prefix}_{timestamp}_{short_uuid}"
    
    @staticmethod
    def generate_uuid() -> str:
        """
        Generate standard UUID v4.
        
        Returns:
            UUID string
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def is_valid_uuid(value: str) -> bool:
        """
        Check if string is valid UUID.
        
        Args:
            value: String to validate
        
        Returns:
            True if valid UUID, False otherwise
        """
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False
```

---

### `date_utils.py` (Phase 2 - Planned)

**Purpose**: Date parsing and validation utilities for TripPreferences required fields (`start_date`, `end_date`, `duration_days`).

**Key Functions**:
```python
from datetime import date, datetime, timedelta
from typing import Optional, Tuple

class DateUtils:
    """Date parsing and validation utilities"""
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[date]:
        """Parse YYYY-MM-DD string to date object"""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None
    
    @staticmethod
    def validate_date_range(
        start_date: str, 
        end_date: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate date range.
        
        Returns:
            (is_valid, error_message)
        """
        start = DateUtils.parse_date(start_date)
        end = DateUtils.parse_date(end_date)
        
        if not start:
            return False, f"Invalid start date: {start_date}"
        if not end:
            return False, f"Invalid end date: {end_date}"
        if end <= start:
            return False, "End date must be after start date"
        if start < date.today():
            return False, "Start date cannot be in the past"
        
        return True, None
    
    @staticmethod
    def calculate_duration(start_date: str, end_date: str) -> int:
        """Calculate duration in days (inclusive)"""
        start = DateUtils.parse_date(start_date)
        end = DateUtils.parse_date(end_date)
        if not start or not end:
            return 0
        return (end - start).days + 1  # Inclusive
    
    @staticmethod
    def format_iso8601(dt: datetime) -> str:
        """Format datetime as ISO-8601 string"""
        return dt.isoformat() + "Z"
```

---

### `logging_utils.py` (Phase 1/2 - Planned)

**Purpose**: Configure structured logging for the application.

**Key Functions**:
```python
import logging
import json
from typing import Dict, Any

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "correlation_id": getattr(record, "correlation_id", None)
        }
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

def setup_logging(level: str = "INFO", format_type: str = "json"):
    """
    Configure application logging.
    
    Args:
        level: Log level (DEBUG|INFO|WARNING|ERROR|CRITICAL)
        format_type: "json" or "text"
    """
    if format_type == "json":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    logging.root.setLevel(level)
    logging.root.addHandler(handler)
```

---

## Non-Negotiable Rules

### ID Generation
1. **ALWAYS use UUID v4** for unique IDs (cryptographically secure)
2. **NEVER use sequential IDs** (predictable, security risk)
3. **Include prefix** for readability (trip_, activity_, req_)
4. **Validate UUIDs** before using in database queries

### Date Handling
1. **ALWAYS use ISO-8601 format** (YYYY-MM-DD for dates, full ISO for datetimes)
2. **ALWAYS use UTC** for timestamps (no local timezone confusion)
3. **Validate date ranges** (end after start, future dates)
4. **Calculate duration inclusively** (both start and end days count)

### Logging
1. **Use structured logging** (JSON format for production)
2. **Include request_id** in all logs for correlation
3. **Redact sensitive data** (API keys, PII, user input)
4. **Log at appropriate levels** (INFO for normal, ERROR for failures)

---

## Logging Requirements

### What to Log (from Utils)
- **INFO**: ID generation, date validation success
- **DEBUG**: UUID validation, date parsing attempts
- **WARNING**: Invalid date formats, deprecated utilities
- **ERROR**: ID generation failures (should never happen)

### Log Examples
```python
logger.info("Trip ID generated", extra={
    "trip_id": trip_id,
    "request_id": request_id
})

logger.debug("Validating date range", extra={
    "start_date": start_date,
    "end_date": end_date
})

logger.warning("Invalid date format", extra={
    "date_str": date_str,
    "expected_format": "YYYY-MM-DD"
})
```

---

## Testing Strategy

### Unit Tests Required (Minimum 10)
1. Test trip ID generation (format, uniqueness)
2. Test activity ID generation
3. Test request ID generation (with timestamp)
4. Test UUID validation (valid UUIDs)
5. Test UUID validation (invalid strings)
6. Test date parsing (valid YYYY-MM-DD)
7. Test date parsing (invalid formats)
8. Test date range validation (valid range)
9. Test date range validation (end before start)
10. Test duration calculation (inclusive)

### Test Examples
```python
def test_generate_trip_id():
    """Test trip ID generation"""
    id1 = IDGenerator.generate_trip_id()
    id2 = IDGenerator.generate_trip_id()
    
    assert id1.startswith("trip_")
    assert id2.startswith("trip_")
    assert id1 != id2  # Unique
    
    # Extract UUID part
    uuid_part = id1.split("_", 1)[1]
    assert IDGenerator.is_valid_uuid(uuid_part)

def test_validate_date_range_valid():
    """Test valid date range"""
    valid, error = DateUtils.validate_date_range("2026-03-15", "2026-03-17")
    
    assert valid == True
    assert error is None

def test_validate_date_range_end_before_start():
    """Test end date before start date"""
    valid, error = DateUtils.validate_date_range("2026-03-17", "2026-03-15")
    
    assert valid == False
    assert "after start" in error.lower()

def test_calculate_duration_inclusive():
    """Test duration calculation (inclusive)"""
    # March 15-17 = 3 days (15, 16, 17)
    duration = DateUtils.calculate_duration("2026-03-15", "2026-03-17")
    
    assert duration == 3
```

---

## Error Handling

### ID Generation Errors
```python
# Should never fail (UUID generation is reliable)
try:
    trip_id = IDGenerator.generate_trip_id()
except Exception as e:
    logger.critical("ID generation failed", exc_info=True)
    raise SystemError("Cannot generate unique IDs")
```

### Date Validation Errors
```python
# Return validation result, don't raise
valid, error = DateUtils.validate_date_range(start, end)
if not valid:
    return {"valid": False, "error": error}
```

---

## Integration Points

### Used By
- All modules needing unique IDs (services, controllers, models)
- All modules needing date validation (models, services)
- All modules needing logging (entire backend)
- NLP extraction and itinerary generation services (Gemini primary / Groq fallback)

### Uses
- Python standard library (`uuid`, `datetime`, `logging`)
- No external dependencies
- LLM configuration comes from `config/settings.py` (Gemini + Groq, no separate gemini.py)

---

## TripPreferences Field Reference

Utilities support the following TripPreferences schema:

**Required Fields (10):** `city`, `country`, `start_date`, `end_date`, `duration_days`, `budget`, `budget_currency`, `interests`, `pace`, `location_preference`

**Optional Fields:** `starting_location` (default: from `location_preference`), `hours_per_day` (default: 8), `transportation_modes` (default: `["mixed"]`), `group_size`, `group_type`, `children_ages`, `dietary_restrictions`, `accessibility_needs`, `weather_tolerance`, `must_see_venues`, `must_avoid_venues`

Date utils specifically validate `start_date`, `end_date`, and compute `duration_days`. ID generator creates trip/activity/request IDs used across all preference and itinerary operations.

---

## LLM Configuration

- **Primary LLM**: Gemini (configured in `config/settings.py`)
- **Fallback LLM**: Groq (configured in `config/settings.py`)
- All LLM configuration is centralized in `settings.py` (no separate `gemini.py`)
- Utils do not directly call LLMs, but generate IDs and validate dates for LLM-powered services

---

## Assumptions
1. UUIDs are sufficiently unique for application needs
2. All dates are in UTC timezone
3. System clock is synchronized (for timestamps)
4. Gemini is the primary LLM; Groq is the fallback

## Open Questions
1. Do we need sortable IDs (ULID instead of UUID)?
2. Should we track ID generation metrics?
3. Do we need custom date formats beyond ISO-8601?

---

**Last Updated**: 2026-02-07  
**Status**: Phase 1 - `id_generator.py` implemented (26 lines), other utilities planned
