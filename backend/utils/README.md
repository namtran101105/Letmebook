# Utils Module - Human Documentation

## Overview

The `utils/` module provides common utility functions and helper classes used throughout the backend. These include ID generation, date handling, logging configuration, and validation helpers.

**Current Status**: Phase 1 - ID generator defined, implementation pending  
**Dependencies**: Python standard library only (no external dependencies)

---

## Purpose

- Generate unique identifiers for trips, activities, and requests
- Parse and validate dates
- Configure structured logging
- Provide common validation functions
- Handle string formatting and sanitization

---

## Files

### `id_generator.py` (Phase 1 - Current)

Generates unique identifiers using UUID v4.

**Key Class**: `IDGenerator`

**Example Usage**:
```python
from backend.utils.id_generator import IDGenerator

# Generate trip ID
trip_id = IDGenerator.generate_trip_id()
# Result: "trip_a1b2c3d4-e5f6-7890-abcd-ef1234567890"

# Generate activity ID
activity_id = IDGenerator.generate_activity_id()
# Result: "activity_12345678-90ab-cdef-1234-567890abcdef"

# Generate request ID (for logging correlation)
request_id = IDGenerator.generate_request_id()
# Result: "req_20260207_143052_a1b2c3d4"

# Validate UUID
is_valid = IDGenerator.is_valid_uuid("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
# Result: True
```

**ID Formats**:
- **Trip ID**: `trip_<uuid>`
- **Activity ID**: `activity_<uuid>`
- **Request ID**: `req_<timestamp>_<short-uuid>`
- **Plain UUID**: `<uuid>`

### `date_utils.py` (Phase 2 - Planned)

Date parsing and validation utilities.

**Example Usage**:
```python
from backend.utils.date_utils import DateUtils

# Parse date string
date_obj = DateUtils.parse_date("2026-03-15")
# Result: date(2026, 3, 15)

# Validate date range
valid, error = DateUtils.validate_date_range("2026-03-15", "2026-03-17")
# Result: (True, None)

# Calculate duration
days = DateUtils.calculate_duration("2026-03-15", "2026-03-17")
# Result: 3 (inclusive: March 15, 16, 17)

# Format as ISO-8601
iso_str = DateUtils.format_iso8601(datetime.now())
# Result: "2026-02-07T14:30:45Z"
```

### `logging_utils.py` (Phase 1/2 - Planned)

Structured logging configuration.

**Example Usage**:
```python
from backend.utils.logging_utils import setup_logging
import logging

# Setup JSON logging
setup_logging(level="INFO", format_type="json")

logger = logging.getLogger(__name__)
logger.info("Trip created", extra={
    "trip_id": "trip_123",
    "request_id": "req_456"
})

# Output (JSON):
# {
#   "timestamp": "2026-02-07T14:30:45",
#   "level": "INFO",
#   "service": "__main__",
#   "message": "Trip created",
#   "trip_id": "trip_123",
#   "request_id": "req_456"
# }
```

---

## ID Generation

### Why UUIDs?

**Universally Unique Identifiers (UUID v4)**:
- Cryptographically random (not predictable)
- No central coordination needed
- Collision probability: ~0% for practical purposes
- 128-bit (32 hexadecimal characters)

**Format**: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`

Example: `a1b2c3d4-e5f6-4890-abcd-ef1234567890`

### ID Prefixes

Prefixes make IDs human-readable:

```python
# Without prefix (confusing)
id1 = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
id2 = "12345678-90ab-cdef-1234-567890abcdef"
# Which is the trip? Which is the activity?

# With prefix (clear)
trip_id = "trip_a1b2c3d4-e5f6-7890-abcd-ef1234567890"
activity_id = "activity_12345678-90ab-cdef-1234-567890abcdef"
# Immediately obvious!
```

### Request IDs for Logging

Request IDs enable **correlation** across logs:

```python
request_id = "req_20260207_143052_a1b2c3d4"

# All logs for this request use same ID
logger.info("Request received", extra={"request_id": request_id})
logger.info("Calling Groq API", extra={"request_id": request_id})
logger.info("Response sent", extra={"request_id": request_id})

# Search logs by request_id to see entire request flow
```

---

## Date Handling

### ISO-8601 Format

**Standard**: All dates use ISO-8601 format

**Date only**: `YYYY-MM-DD`  
Example: `2026-03-15`

**Date with time**: `YYYY-MM-DDTHH:MM:SSZ`  
Example: `2026-03-15T14:30:45Z`

### UTC Timezone

**Always use UTC** for timestamps to avoid timezone confusion:

```python
# ✅ Good - UTC timestamp
"2026-03-15T14:30:45Z"

# ❌ Bad - Local timezone (ambiguous)
"2026-03-15 14:30:45"  # EST? PST? Unknown!
```

### Inclusive Duration

Date ranges are **inclusive** (both start and end days count):

```python
# March 15-17 = 3 days
start = "2026-03-15"  # Day 1
end = "2026-03-17"    # Day 3
duration = (end - start).days + 1 = 3 days

# Activities can span all 3 days:
# - Day 1: March 15
# - Day 2: March 16  
# - Day 3: March 17
```

---

## Logging

### Structured Logging

**JSON Format** (production):
```json
{
  "timestamp": "2026-02-07T14:30:45",
  "level": "INFO",
  "service": "nlp_extraction_service",
  "message": "Extraction successful",
  "request_id": "req_123",
  "fields_extracted": 12,
  "completeness_score": 0.85
}
```

**Text Format** (development):
```
2026-02-07 14:30:45 - nlp_extraction_service - INFO - Extraction successful
```

### Log Levels

Use appropriate log levels:

- **DEBUG**: Detailed diagnostic information
- **INFO**: Normal operations (request start/end, success)
- **WARNING**: Non-critical issues (retries, tight budget)
- **ERROR**: Operation failures (API errors, validation failures)
- **CRITICAL**: System-level failures (cannot start, database down)

### Request Correlation

Every log should include `request_id`:

```python
# Generate at request start
request_id = IDGenerator.generate_request_id()

# Pass to all operations
preferences = await nlp_service.extract_preferences(
    user_input, 
    request_id=request_id
)

# All logs use same request_id for correlation
```

---

## Testing

### Running Tests

```bash
# All utils tests
pytest backend/tests/utils/ -v

# ID generator only
pytest backend/tests/utils/test_id_generator.py -v

# Date utils only
pytest backend/tests/utils/test_date_utils.py -v
```

### Test Coverage

**Target**: 95% coverage for utils

### Key Test Cases

#### ID Generation
1. ✅ Generate trip ID (starts with "trip_")
2. ✅ Generate activity ID (starts with "activity_")
3. ✅ Generate request ID (includes timestamp)
4. ✅ IDs are unique (no duplicates)
5. ✅ UUID validation (valid UUID)
6. ✅ UUID validation (invalid string)

#### Date Utils
7. ✅ Parse valid date (YYYY-MM-DD)
8. ✅ Parse invalid date (returns None)
9. ✅ Validate range (end after start)
10. ✅ Reject range (end before start)
11. ✅ Reject past start date
12. ✅ Calculate duration (inclusive)

---

## Common Issues

### Issue: "IDs are predictable"

**Cause**: Not using UUID v4 (using sequential IDs)

**Solution**: Always use `IDGenerator.generate_*()` methods, never manual IDs.

### Issue: "Date parsing fails"

**Cause**: Date string not in YYYY-MM-DD format

**Solution**:
```python
# ❌ Wrong formats
"03/15/2026"  # MM/DD/YYYY
"15-03-2026"  # DD-MM-YYYY
"March 15, 2026"

# ✅ Correct format
"2026-03-15"  # YYYY-MM-DD
```

### Issue: "Duration off by one"

**Cause**: Forgetting to add +1 for inclusive range

**Solution**:
```python
# ❌ Wrong (exclusive end)
duration = (end_date - start_date).days  # 2 days

# ✅ Correct (inclusive)
duration = (end_date - start_date).days + 1  # 3 days
```

---

## Best Practices

### ID Generation

1. **Use prefixes** for human readability
2. **Validate UUIDs** before database queries
3. **Generate at creation time** (not lazily)
4. **Include in all logs** for correlation

### Date Handling

1. **Always validate** date ranges
2. **Use ISO-8601** format consistently
3. **Store in UTC**, display in local timezone
4. **Calculate duration** inclusively

### Logging

1. **Include request_id** in all logs
2. **Use structured format** (JSON) in production
3. **Redact sensitive data** (API keys, PII)
4. **Log at appropriate level** (not everything is INFO)

---

## API Reference

### `IDGenerator`

**Static Methods**:

**`generate_trip_id(prefix: str = "trip") -> str`**

Generate unique trip ID.

**`generate_activity_id(prefix: str = "activity") -> str`**

Generate unique activity ID.

**`generate_request_id(prefix: str = "req") -> str`**

Generate unique request ID with timestamp.

**`generate_uuid() -> str`**

Generate plain UUID v4.

**`is_valid_uuid(value: str) -> bool`**

Check if string is valid UUID.

### `DateUtils` (Planned)

**Static Methods**:

**`parse_date(date_str: str) -> Optional[date]`**

Parse YYYY-MM-DD string to date object.

**`validate_date_range(start: str, end: str) -> Tuple[bool, Optional[str]]`**

Validate date range. Returns (is_valid, error_message).

**`calculate_duration(start: str, end: str) -> int`**

Calculate duration in days (inclusive).

**`format_iso8601(dt: datetime) -> str`**

Format datetime as ISO-8601 string.

---

## Contributing

When adding new utilities:

1. **Keep functions pure** (no side effects when possible)
2. **Add comprehensive tests** (95%+ coverage)
3. **Document in CLAUDE.md** (agent instructions)
4. **Document in README.md** (human guide with examples)
5. **Follow naming conventions** (`*_utils.py`)

---

**Last Updated**: 2026-02-07  
**Maintained By**: Backend Team  
**Questions**: See `backend/utils/CLAUDE.md` for detailed agent instructions
