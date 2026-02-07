# Storage Module - Agent Instructions

**Parent Contexts**:
- `MONVOYAGE/CLAUDE.md` (project-wide architecture, testing conventions)
- `MONVOYAGE/backend/CLAUDE_EMBEDDED.md` (backend operational rules, MVP requirements)

**Module Purpose**: Data persistence layer implementing repository pattern. Handles saving/loading trip preferences and itineraries to JSON files (Phase 1) or MongoDB (Phase 2+).

---

## Module Responsibilities

### Current (Phase 1)
1. **JSON File Storage** - Save and load trip data to/from JSON files
2. File-based repositories for trips and itineraries
3. Simple file I/O operations
4. Local data persistence for development

### Planned (Phase 2/3)
5. **MongoDB Integration** - Replace JSON files with MongoDB
6. Database connection management
7. Query optimization
8. Data migration utilities

---

## Files in This Module

### `trip_json_repo.py` (Phase 1 - Current)

**Purpose**: Repository for trip preferences using JSON file storage.

**Must Include**:
```python
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

class TripJsonRepository:
    """Repository for trip preferences stored in JSON files"""
    
    def __init__(self, storage_dir: str = "data/trips"):
        self.logger = logging.getLogger(__name__)
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, trip_id: str, preferences: Dict[str, Any]) -> None:
        """
        Save trip preferences to JSON file.
        
        Args:
            trip_id: Unique trip identifier (e.g., trip_20260207_abc123)
            preferences: Trip preferences as dict
        
        Raises:
            IOError: If file write fails
        """
        file_path = self.storage_dir / f"{trip_id}.json"
        
        # Add metadata
        data = {
            "trip_id": trip_id,
            "preferences": preferences,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Trip saved", extra={
                "trip_id": trip_id,
                "file": str(file_path)
            })
        except Exception as e:
            self.logger.error("Failed to save trip", extra={
                "trip_id": trip_id,
                "error": str(e)
            }, exc_info=True)
            raise
    
    def load(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """
        Load trip preferences from JSON file.
        
        Args:
            trip_id: Unique trip identifier
        
        Returns:
            Dict with trip data or None if not found
        """
        file_path = self.storage_dir / f"{trip_id}.json"
        
        if not file_path.exists():
            self.logger.warning("Trip not found", extra={
                "trip_id": trip_id
            })
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.debug("Trip loaded", extra={
                "trip_id": trip_id
            })
            return data
        except Exception as e:
            self.logger.error("Failed to load trip", extra={
                "trip_id": trip_id,
                "error": str(e)
            }, exc_info=True)
            raise
    
    def list_all(self) -> List[str]:
        """
        List all trip IDs.
        
        Returns:
            List of trip IDs
        """
        trip_files = self.storage_dir.glob("trip_*.json")
        trip_ids = [f.stem for f in trip_files]
        
        self.logger.debug("Listed trips", extra={
            "count": len(trip_ids)
        })
        return trip_ids
    
    def delete(self, trip_id: str) -> bool:
        """
        Delete trip by ID.
        
        Args:
            trip_id: Trip to delete
        
        Returns:
            True if deleted, False if not found
        """
        file_path = self.storage_dir / f"{trip_id}.json"
        
        if not file_path.exists():
            return False
        
        try:
            file_path.unlink()
            self.logger.info("Trip deleted", extra={
                "trip_id": trip_id
            })
            return True
        except Exception as e:
            self.logger.error("Failed to delete trip", extra={
                "trip_id": trip_id,
                "error": str(e)
            }, exc_info=True)
            raise
```

---

### `itinerary_json_repo.py` (Phase 1 - Current)

**Purpose**: Repository for itineraries using JSON file storage.

**Must Include**:
```python
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

class ItineraryJsonRepository:
    """Repository for itineraries stored in JSON files"""
    
    def __init__(self, storage_dir: str = "data/itineraries"):
        self.logger = logging.getLogger(__name__)
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, trip_id: str, itinerary: Dict[str, Any]) -> None:
        """
        Save itinerary to JSON file.
        
        Args:
            trip_id: Associated trip ID
            itinerary: Itinerary data as dict
        """
        file_path = self.storage_dir / f"{trip_id}_itinerary.json"
        
        data = {
            "trip_id": trip_id,
            "itinerary": itinerary,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.logger.info("Itinerary saved", extra={
            "trip_id": trip_id,
            "file": str(file_path)
        })
    
    def load(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """
        Load itinerary by trip ID.
        
        Args:
            trip_id: Trip to get itinerary for
        
        Returns:
            Itinerary data or None if not found
        """
        file_path = self.storage_dir / f"{trip_id}_itinerary.json"
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
```

---

## Non-Negotiable Rules

### Repository Pattern
1. **Abstract storage details** - Controllers/services don't know about files/DB
2. **Consistent interface** - save(), load(), delete(), list_all()
3. **Type hints** - All methods use type annotations
4. **Error handling** - Catch and log I/O errors
5. **No business logic** - Only data persistence

### File Storage (Phase 1)
1. **Create directories** - Use `mkdir(parents=True, exist_ok=True)`
2. **UTF-8 encoding** - All file operations use UTF-8
3. **Pretty JSON** - Use `indent=2` for readability
4. **Atomic writes** - Consider using temp files for critical data
5. **Metadata** - Include created_at, updated_at timestamps

### MongoDB (Phase 2) - Planned
1. **Connection pooling** - Reuse connections
2. **Index all IDs** - trip_id, user_id, etc.
3. **TTL indexes** - Auto-delete old data
4. **Validate schemas** - Use MongoDB schema validation
5. **Transactions** - Use for multi-document operations

---

## Logging Requirements

### What to Log
- **INFO**: Save/load operations (with IDs)
- **DEBUG**: List operations, query details
- **WARNING**: Not found errors
- **ERROR**: I/O failures, database errors

### Log Examples
```python
# Save operation
logger.info("Trip saved", extra={
    "trip_id": trip_id,
    "file": str(file_path)
})

# Not found
logger.warning("Trip not found", extra={
    "trip_id": trip_id
})

# Error
logger.error("Failed to save trip", extra={
    "trip_id": trip_id,
    "error": str(e)
}, exc_info=True)
```

---

## Testing Strategy

### Unit Tests Required (Minimum 10)
1. Test save trip (success)
2. Test load trip (exists)
3. Test load trip (not found)
4. Test list all trips
5. Test delete trip (exists)
6. Test delete trip (not found)
7. Test save itinerary
8. Test load itinerary
9. Test directory creation
10. Test error handling (permissions)

### Integration Tests Required (Minimum 3)
1. Test save and load round-trip
2. Test multiple trips
3. Test concurrent access

### Test Examples
```python
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

def test_save_and_load_trip(temp_storage):
    """Test saving and loading trip"""
    repo = TripJsonRepository(storage_dir=temp_storage)
    
    preferences = {
        "start_date": "2026-03-15",
        "end_date": "2026-03-17",
        "budget": 200.0
    }
    
    # Save
    repo.save("trip_123", preferences)
    
    # Load
    loaded = repo.load("trip_123")
    assert loaded is not None
    assert loaded["trip_id"] == "trip_123"
    assert loaded["preferences"]["budget"] == 200.0

def test_load_nonexistent_trip(temp_storage):
    """Test loading trip that doesn't exist"""
    repo = TripJsonRepository(storage_dir=temp_storage)
    result = repo.load("trip_999")
    assert result is None

def test_list_all_trips(temp_storage):
    """Test listing all trips"""
    repo = TripJsonRepository(storage_dir=temp_storage)
    
    repo.save("trip_1", {"budget": 100})
    repo.save("trip_2", {"budget": 200})
    
    all_trips = repo.list_all()
    assert len(all_trips) == 2
    assert "trip_1" in all_trips
    assert "trip_2" in all_trips
```

---

## Phase 2: MongoDB Migration

### Planned Collections

**trips** collection:
```javascript
{
  _id: ObjectId,
  trip_id: "trip_20260207_abc123",
  preferences: {
    start_date: "2026-03-15",
    end_date: "2026-03-17",
    budget: 200.0,
    // ... other fields
  },
  created_at: ISODate("2026-02-07T14:30:00Z"),
  updated_at: ISODate("2026-02-07T14:30:00Z"),
  user_id: "user_123"  // Phase 2
}

// Indexes
db.trips.createIndex({ trip_id: 1 }, { unique: true })
db.trips.createIndex({ user_id: 1 })
db.trips.createIndex({ created_at: 1 })
```

**itineraries** collection:
```javascript
{
  _id: ObjectId,
  trip_id: "trip_20260207_abc123",
  itinerary: {
    days: [...],
    budget_breakdown: {...}
  },
  created_at: ISODate,
  updated_at: ISODate
}

// Indexes
db.itineraries.createIndex({ trip_id: 1 }, { unique: true })
```

### Migration Strategy
1. Create MongoDB repositories alongside JSON repos
2. Support both backends via feature flag
3. Migrate data using migration script
4. Switch to MongoDB
5. Remove JSON repos

---

## Error Handling

### File I/O Errors
```python
try:
    with open(file_path, 'w') as f:
        json.dump(data, f)
except PermissionError:
    logger.error("Permission denied", extra={
        "file": str(file_path)
    })
    raise StorageError("Cannot write to storage directory")
except Exception as e:
    logger.error("Unexpected error", exc_info=True)
    raise
```

### Custom Exceptions
```python
class StorageError(Exception):
    """Base storage error"""
    pass

class TripNotFoundError(StorageError):
    """Trip not found in storage"""
    def __init__(self, trip_id: str):
        self.trip_id = trip_id
        super().__init__(f"Trip not found: {trip_id}")
```

---

## Integration Points

### Used By
- `controllers/trip_controller.py` - Save/load trips
- `services/itinerary_service.py` - Save/load itineraries

### Uses
- Python standard library (`json`, `pathlib`)
- Phase 2: `pymongo` for MongoDB

---

## Assumptions
1. JSON files sufficient for Phase 1 (limited users)
2. File system is writable
3. Trip IDs are unique
4. No concurrent write conflicts (single-user development)

## Open Questions
1. Should we implement file locking for concurrent access?
2. What's the backup strategy for JSON files?
3. How to handle data migration to MongoDB?
4. Should repositories be async in Phase 2?

---

**Last Updated**: 2026-02-07  
**Status**: Phase 1 - Documentation Complete, Implementation Pending
