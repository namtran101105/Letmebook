# Quick Reference: Booking Preferences Flow

## How It Works

The system now asks about booking preferences **after** collecting all basic trip information:

### Question Flow Order:
1. **City** - "Which city do you want to visit?"
2. **Country** - "Which country is that city in?"
3. **Location Preference** (optional) - "Where in the city will you stay?"
4. **Dates** - "When will you travel?"
5. **Interests** - "What are you interested in?"
6. **Pace** - "What pace do you prefer?"
7. **Budget** - "What's your budget?"
8. ✨ **NEW: Booking Type** - "Would you like to book accommodation, transportation, or both?"
9. ✨ **NEW: Source Location** (conditional) - "Where will you be traveling from?"

---

## Booking Type Options

### Option 1: "Accommodation" (Airbnb only)
- User says: "Just Airbnb", "Only accommodation", "I need a place to stay"
- Result: `booking_type = "accommodation"`
- Source location: **NOT ASKED** ✅
- Complete at: 100%

### Option 2: "Transportation" (Flight/Bus only)
- User says: "Just flight tickets", "Only transportation", "I need a bus ticket"
- Result: `booking_type = "transportation"`
- Source location: **ASKED** ✅ "Where will you be traveling from?"
- Complete at: 100% (after source is provided)

### Option 3: "Both" (Accommodation + Transportation)
- User says: "Both", "Everything", "Accommodation and flights"
- Result: `booking_type = "both"`
- Source location: **ASKED** ✅ "Where will you be traveling from?"
- Complete at: 100% (after source is provided)

### Option 4: "None" (No booking needed) ⭐ NEW
- User says: "No", "Nothing", "I don't need", "No thanks", "I'll book myself"
- Result: `booking_type = "none"`
- Source location: **NOT ASKED** ✅
- Complete at: 100% - **Goes straight to confirmation!**

---

## Example Conversations

### 🏠 Accommodation Only

```
Bot: What's your budget?
User: $500

Bot: Would you like to book accommodation, transportation, or both?
User: Just Airbnb

Bot: Perfect! I have your Kingston trip from Feb 15-17. Shall I proceed? ✅
(No source location asked)
```

### ✈️ Transportation Only

```
Bot: What's your budget?
User: $500

Bot: Would you like to book accommodation, transportation, or both?
User: Just flight tickets

Bot: Got it! Where will you be traveling from?
User: Toronto

Bot: Perfect! I have your Kingston trip from Toronto. Shall I proceed? ✅
```

### 🏠✈️ Both

```
Bot: What's your budget?
User: $500

Bot: Would you like to book accommodation, transportation, or both?
User: Both please

Bot: Great! Where will you be traveling from?
User: Montreal

Bot: Perfect! I have your Kingston trip from Montreal. Shall I proceed? ✅
```

### 🚫 No Booking Needed

```
Bot: What's your budget?
User: $500

Bot: Would you like to book accommodation, transportation, or both? (or say 'no' if you don't need booking)
User: No

Bot: Perfect! I have your Kingston trip from Feb 15-17. Shall I proceed? ✅
(No more questions - goes straight to confirmation!)
```

---

## Data Storage

### Stored in JSON:
```json
{
  "booking_type": "both",
  "source_location": "Toronto"
}
```

### Displayed on UI:
```
🎫 Booking Preferences
Booking Type: Both Accommodation & Transportation
```

**Note:** `source_location` is **stored in JSON** but **NOT shown on the UI** as requested.

---

## Testing the Feature

```bash
# Start the backend
cd backend
python app.py

# In browser, go to: http://localhost:5000
# Try different booking scenarios
```

Sample test inputs:
- "I want to visit Kingston for 3 days with $500 budget, museums, relaxed pace, just need Airbnb"
- "Trip to Toronto next week, $800, food tours, moderate, need flight and hotel from Montreal"
- "Paris in summer, $2000, all interests, packed, transportation only from New York"
