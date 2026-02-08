# Booking Preferences Implementation

## Overview
Updated the NLP extraction service to support conditional booking preferences. Users can now specify if they want to book:
- **Accommodation only** (Airbnb)
- **Transportation only** (Flight/Bus)  
- **Both** (Accommodation + Transportation)

The system now **conditionally asks for source location** only when transportation is involved.

---

## Changes Made

### 1. **TripPreferences Model** (`backend/models/trip_preferences.py`)

Added two new fields:

```python
# Booking preferences
booking_type: Optional[str] = None  # "accommodation", "transportation", or "both"
source_location: Optional[str] = None  # Where user is traveling from (only needed if booking_type includes transportation)
```

### 2. **NLP Extraction Service** (`backend/services/nlp_extraction_service.py`)

#### Updated System Instruction
- Added booking_type to extraction instructions
- Added source_location with conditional requirement

#### Updated JSON Schema
Added fields:
```python
"booking_type": "string or null ('accommodation', 'transportation', or 'both')",
"source_location": "string or null (where user is traveling from - only needed if booking_type is 'transportation' or 'both')"
```

#### Updated Conversation Flow
Added two new priority levels:
- **Priority 7**: Ask for booking_type after all basic preferences
- **Priority 8**: Ask for source_location only if `booking_type` is "transportation" or "both"

#### Updated Completeness Calculation
- `booking_type` is always required
- `source_location` is conditionally required based on `booking_type`

```python
# Add source_location as required if booking includes transportation
if preferences.booking_type in ["transportation", "both"]:
    required_fields.append('source_location')
```

### 3. **Frontend Display** (`frontend/index.html`)

#### Updated Results Panel
- Added new "Booking Preferences" card
- Shows booking_type with user-friendly labels
- **Does NOT display source_location** (hidden from UI as requested)

Example display:
```
🎫 Booking Preferences
Booking Type: Both Accommodation & Transportation
```

---

## User Flow

### Scenario 1: Accommodation Only
1. User provides: city, country, dates, budget, interests, pace
2. System asks: "Would you like to book accommodation, transportation, or both?"
3. User answers: "Just Airbnb" → `booking_type = "accommodation"`
4. ✅ **No source location needed** → Flow complete at 100%

### Scenario 2: Transportation Only
1. User provides: city, country, dates, budget, interests, pace
2. System asks: "Would you like to book accommodation, transportation, or both?"
3. User answers: "Just flight tickets" → `booking_type = "transportation"`
4. System asks: "Where will you be traveling from?" → Gets source_location
5. ✅ Flow complete at 100%

### Scenario 3: Both
1. User provides: city, country, dates, budget, interests, pace
2. System asks: "Would you like to book accommodation, transportation, or both?"
3. User answers: "Both" → `booking_type = "both"`
4. System asks: "Where will you be traveling from?" → Gets source_location
5. ✅ Flow complete at 100%

---

## Data Storage

### JSON Output
```json
{
  "city": "Kingston",
  "country": "Canada",
  "start_date": "2026-03-15",
  "end_date": "2026-03-17",
  "budget": 500.0,
  "interests": ["Culture and History"],
  "pace": "relaxed",
  "booking_type": "both",
  "source_location": "Toronto"  // Included in JSON but NOT shown on UI
}
```

---

## Testing

Run the test script to verify the conditional logic:

```bash
cd backend
python test_booking_flow.py
```

This will test:
- ✅ Accommodation only (no source needed)
- ✅ Transportation only (source required)
- ✅ Both (source required)
- ✅ No booking type (incomplete)

---

## Key Features

✅ **Conditional logic** - source_location only asked when needed  
✅ **Hidden from UI** - source_location stored in JSON but not displayed  
✅ **Flexible booking** - Supports 3 booking types  
✅ **Smart validation** - Completeness score adjusts based on booking_type  
✅ **Backward compatible** - Existing trips without booking_type still work  

---

## API Response Example

```json
{
  "success": true,
  "preferences": {
    "city": "Kingston",
    "booking_type": "both",
    "source_location": "Toronto"  // Present in data
  },
  "validation": {
    "completeness_score": 1.0,
    "valid": true
  },
  "bot_message": "Perfect! I have your Kingston trip from Toronto. Shall I proceed with planning?"
}
```

The frontend displays booking_type but **intentionally omits source_location** from the UI.
