# Storage Module - Human Documentation

## Overview

The `storage/` module implements the repository pattern for data persistence. Currently uses JSON files (Phase 1) with planned MongoDB migration (Phase 2).

**Current Status**: Phase 1 - JSON file storage  
**Dependencies**: Python standard library (`json`, `pathlib`)

---

## Purpose

- Abstract data storage details from business logic
- Provide consistent interface for saving/loading data
- Support easy migration to MongoDB in Phase 2
- Enable testing with mock repositories

---

## Files

### `trip_json_repo.py` (Phase 1 - Current)

Repository for trip preferences stored as JSON files.

**Location**: `data/trips/`

**Methods**:

#### `save(trip_id, preferences)`
Save trip preferences to JSON file.

**Example**:
```python
from storage.trip_json_repo import TripJsonRepository

repo = TripJsonRepository()
repo.save(
    trip_id="trip_20260207_abc123",
    preferences={
        # Required fields (10)
        "city": "Kingston",
        "country": "Canada",
        "start_date": "2026-03-15",
        "end_date": "2026-03-17",
        "duration_days": 3,
        "budget": 200.0,
        "budget_currency": "CAD",
        "interests": ["history", "food"],
        "pace": "moderate",
        "location_preference": "downtown",
        # Optional fields
        "hours_per_day": 8,
        "transportation_modes": ["mixed"]
    }
)

# Creates: data/trips/trip_20260207_abc123.json
```

#### `load(trip_id)`
Load trip preferences from JSON file.

**Example**:
```python
data = repo.load("trip_20260207_abc123")

# Returns:
{
    "trip_id": "trip_20260207_abc123",
    "preferences": {
        "start_date": "2026-03-15",
        ...
    },
    "created_at": "2026-02-07T14:30:00",
    "updated_at": "2026-02-07T14:30:00"
}

# Returns None if not found
```

#### `list_all()`
List all trip IDs.

**Example**:
```python
trip_ids = repo.list_all()
# Returns: ["trip_001", "trip_002", "trip_003"]
```

#### `delete(trip_id)`
Delete trip by ID.

**Example**:
```python
deleted = repo.delete("trip_20260207_abc123")
# Returns: True if deleted, False if not found
```

---

### `itinerary_json_repo.py` (Phase 1 - Current)

Repository for itineraries stored as JSON files.

**Location**: `data/itineraries/`

**Methods**:

#### `save(trip_id, itinerary)`
Save itinerary for a trip.

**Example**:
```python
from storage.itinerary_json_repo import ItineraryJsonRepository

repo = ItineraryJsonRepository()
repo.save(
    trip_id="trip_20260207_abc123",
    itinerary={
        "days": [
            {
                "date": "2026-03-15",
                "activities": [...]
            }
        ]
    }
)

# Creates: data/itineraries/trip_20260207_abc123_itinerary.json
```

#### `load(trip_id)`
Load itinerary for a trip.

**Example**:
```python
data = repo.load("trip_20260207_abc123")
# Returns itinerary data or None if not found
```

---

## Repository Pattern

### Why Repository Pattern?

**Benefits**:
1. **Abstraction** - Business logic doesn't know about storage
2. **Testability** - Easy to mock repositories
3. **Flexibility** - Swap JSON for MongoDB without changing controllers
4. **Consistency** - All repositories have same interface

### Pattern Structure

```
Controller/Service
    ↓
Repository (Interface)
    ↓
Storage Backend (JSON files or MongoDB)
```

---

## File Storage (Phase 1)

### Directory Structure

```
MonVoyage/
├── data/
│   ├── trips/
│   │   ├── trip_20260207_abc123.json
│   │   ├── trip_20260207_def456.json
│   │   └── ...
│   └── itineraries/
│       ├── trip_20260207_abc123_itinerary.json
│       ├── trip_20260207_def456_itinerary.json
│       └── ...
```

### JSON File Format

**Trip file** (`trip_20260207_abc123.json`):
```json
{
  "trip_id": "trip_20260207_abc123",
  "preferences": {
    "city": "Kingston",
    "country": "Canada",
    "start_date": "2026-03-15",
    "end_date": "2026-03-17",
    "duration_days": 3,
    "budget": 200.0,
    "budget_currency": "CAD",
    "interests": ["history", "food"],
    "pace": "moderate",
    "location_preference": "downtown",
    "starting_location": "downtown",
    "hours_per_day": 8,
    "transportation_modes": ["mixed"],
    "dietary_restrictions": ["vegetarian"],
    "group_size": null,
    "group_type": null,
    "children_ages": [],
    "accessibility_needs": [],
    "weather_tolerance": null,
    "must_see_venues": [],
    "must_avoid_venues": []
  },
  "created_at": "2026-02-07T14:30:00",
  "updated_at": "2026-02-07T15:45:00"
}
```

**Itinerary file** (`trip_20260207_abc123_itinerary.json`):
```json
{
  "trip_id": "trip_20260207_abc123",
  "itinerary": {
    "days": [
      {
        "date": "2026-03-15",
        "activities": [...]
      }
    ],
    "budget_breakdown": {...}
  },
  "created_at": "2026-02-07T16:00:00",
  "updated_at": "2026-02-07T16:00:00"
}
```

---

## MongoDB Migration (Phase 2 - Planned)

### Planned Collections

**trips**:
- Fields: trip_id, preferences (10 required + optional fields), user_id, created_at, updated_at
- Required preference fields: city, country, start_date, end_date, duration_days, budget, budget_currency, interests, pace, location_preference
- Optional preference fields: starting_location, hours_per_day, transportation_modes, group_size, group_type, children_ages, dietary_restrictions, accessibility_needs, weather_tolerance, must_see_venues, must_avoid_venues
- Indexes: trip_id (unique), user_id, created_at

**itineraries**:
- Fields: trip_id, itinerary, created_at, updated_at
- Indexes: trip_id (unique)

### Migration Steps

1. **Create MongoDB repositories** (`trip_mongo_repo.py`)
2. **Add feature flag** to switch between JSON/MongoDB
3. **Run migration script** to copy JSON → MongoDB
4. **Test with MongoDB** backend
5. **Remove JSON repositories**

### Example MongoDB Repository

```python
from pymongo import MongoClient

class TripMongoRepository:
    def __init__(self, connection_string: str):
        self.client = MongoClient(connection_string)
        self.db = self.client.monvoyage
        self.collection = self.db.trips
    
    def save(self, trip_id: str, preferences: Dict):
        self.collection.update_one(
            {"trip_id": trip_id},
            {
                "$set": {
                    "preferences": preferences,
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "trip_id": trip_id,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
    
    def load(self, trip_id: str) -> Optional[Dict]:
        return self.collection.find_one({"trip_id": trip_id})
```

---

## Testing

### Running Tests

```bash
# All storage tests
pytest backend/tests/storage/ -v

# Specific repository
pytest backend/tests/storage/test_trip_json_repo.py -v

# With coverage
pytest backend/tests/storage/ --cov=backend/storage --cov-report=html
```

### Test Examples

```python
import pytest
import tempfile
from storage.trip_json_repo import TripJsonRepository

@pytest.fixture
def temp_repo():
    """Create repository with temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield TripJsonRepository(storage_dir=tmpdir)

def test_save_and_load(temp_repo):
    """Test round-trip save/load with required fields"""
    preferences = {
        "city": "Kingston", "country": "Canada",
        "start_date": "2026-03-15", "end_date": "2026-03-17",
        "duration_days": 3, "budget": 200.0, "budget_currency": "CAD",
        "interests": ["history"], "pace": "moderate",
        "location_preference": "downtown"
    }
    temp_repo.save("trip_123", preferences)

    loaded = temp_repo.load("trip_123")
    assert loaded["preferences"]["budget"] == 200.0
    assert loaded["preferences"]["city"] == "Kingston"

def test_load_nonexistent(temp_repo):
    """Test loading non-existent trip"""
    result = temp_repo.load("trip_999")
    assert result is None

def test_delete(temp_repo):
    """Test deleting trip"""
    temp_repo.save("trip_123", {})
    deleted = temp_repo.delete("trip_123")
    assert deleted == True
    
    loaded = temp_repo.load("trip_123")
    assert loaded is None
```

### Key Test Cases

1. ✅ Save trip (new file created)
2. ✅ Load trip (file exists)
3. ✅ Load trip (file doesn't exist)
4. ✅ Update trip (file overwritten)
5. ✅ Delete trip (file removed)
6. ✅ List all trips
7. ✅ Save itinerary
8. ✅ Load itinerary
9. ✅ Directory auto-creation
10. ✅ UTF-8 encoding
11. ✅ Error handling (permissions)
12. ✅ Concurrent access

---

## Common Issues

### Issue: Permission denied

**Symptom**: `PermissionError` when saving

**Solution**: Check directory permissions
```bash
# Ensure data directory is writable
chmod 755 data/
chmod 755 data/trips/
chmod 755 data/itineraries/
```

### Issue: Trip not found

**Symptom**: `load()` returns `None`

**Solution**: Verify trip ID and file exists
```python
# Check if file exists
from pathlib import Path
file_path = Path("data/trips/trip_123.json")
print(file_path.exists())

# List all trips
repo = TripJsonRepository()
print(repo.list_all())
```

### Issue: JSON decode error

**Symptom**: `JSONDecodeError` when loading

**Solution**: Check file format
```bash
# Validate JSON file
cat data/trips/trip_123.json | python -m json.tool
```

---

## Best Practices

### 1. Always Use Repository

```python
# ❌ BAD - Direct file access
with open("data/trips/trip_123.json") as f:
    data = json.load(f)

# ✅ GOOD - Use repository
repo = TripJsonRepository()
data = repo.load("trip_123")
```

### 2. Handle Not Found

```python
data = repo.load("trip_123")
if data is None:
    # Handle not found
    raise TripNotFoundError("trip_123")
```

### 3. Check Delete Result

```python
deleted = repo.delete("trip_123")
if not deleted:
    # Trip didn't exist
    logger.warning("Trip not found for deletion")
```

### 4. Use Type Hints

```python
def save_trip(repo: TripJsonRepository, trip_id: str) -> None:
    # Type hints make code clearer
    ...
```

### 5. Test with Temporary Directory

```python
# Always use temp directory for tests
with tempfile.TemporaryDirectory() as tmpdir:
    repo = TripJsonRepository(storage_dir=tmpdir)
    # ... test code ...
```

---

## Integration Example

### Controller Using Repository

```python
from storage.trip_json_repo import TripJsonRepository

class TripController:
    def __init__(self):
        self.trip_repo = TripJsonRepository()

    async def save_trip(self, trip_id: str, preferences: Dict):
        # Validate preferences (checks 10 required fields)
        trip = TripPreferences.from_dict(preferences)
        validation = trip.validate()

        if not validation["valid"]:
            raise ValidationError(validation["issues"])

        # Save to storage (includes required + optional fields)
        self.trip_repo.save(trip_id, preferences)

        return {"success": True, "trip_id": trip_id}

    async def get_trip(self, trip_id: str):
        # Load from storage
        data = self.trip_repo.load(trip_id)

        if data is None:
            raise TripNotFoundError(trip_id)

        return data
```

---

## Future Enhancements (Phase 2/3)

### Phase 2
- [ ] MongoDB integration
- [ ] Connection pooling
- [ ] Database indexes
- [ ] Migration scripts
- [ ] Async repository methods

### Phase 3
- [ ] Multi-user support
- [ ] Data versioning
- [ ] Soft deletes
- [ ] Audit logging
- [ ] Backup/restore utilities

---

## Contributing

When modifying storage layer:

1. **Maintain interface** - Don't break existing methods
2. **Add tests** - Cover new functionality
3. **Update both repos** - JSON and future MongoDB
4. **Document changes** - Update this README
5. **Test migration** - Ensure data migrates correctly

---

**Last Updated**: 2026-02-07  
**Maintained By**: Backend Team  
**Questions**: See `backend/storage/CLAUDE.md` for detailed agent instructions
