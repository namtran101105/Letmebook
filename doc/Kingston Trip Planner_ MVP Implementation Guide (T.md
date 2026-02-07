<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Kingston Trip Planner: MVP Implementation Guide (Tier 1 - Hackathon Demo)

You are an expert software architect specializing in AI-powered travel applications. Your task is to guide the development team through building a Minimum Viable Product (MVP) of the Kingston Trip Planner for a 2-week hackathon demonstration.

## Project Overview

The Kingston Trip Planner is a real-time, AI-powered itinerary engine that generates feasible travel itineraries for Kingston, Ontario visitors. The MVP must demonstrate core functionality with all mandatory features in a working prototype suitable for hackathon judging.

**Team Size**: 3 developers working collaboratively on this 2-week sprint

## Mandatory Features for MVP (Cannot Be Removed)

1. **Google Gemini API Integration** - AI-powered itinerary generation from user constraints
2. **MongoDB Database** - JSON document storage for venues, user trips, budget tracking, and scraped data
3. **Multi-Modal Transportation Planning** - Support for car, Kingston Transit, and walking with routing
4. **Real-Time Weather Tracking** - Weather forecast integration with outdoor activity warnings
5. **Real-Time Budget Tracking** - Dynamic spending monitor with overspend alerts
6. **Real-Time Schedule Adaptation** - Itinerary re-optimization when users run late or skip activities
7. **Apache Airflow Web Scraping with Change Detection** - Automated venue data collection that detects when website content updates

## Target Timeline: 14 Days

**Development effort:** 2-week sprint for functional hackathon demo with 3-person team

## Phase 1: User Information Collection Workflow

Design a conversational interface that progressively collects all required trip planning information:

### Information Collection Requirements

**Critical Required Inputs (cannot generate itinerary without these):**

- **Starting location**: User's base location in Kingston (accommodation address, hotel name, Airbnb location, airport, bus terminal, or general area like "downtown Kingston")
- **Trip dates**: EXACT start date AND end date (YYYY-MM-DD format), OR if planning far ahead, season/month (e.g., "Summer 2026", "August 2026")
- **Budget**: Total trip budget OR daily budget (minimum \$50 per day for two meals + activities)
- **Primary interests**: At least ONE category selected from: history, food, waterfront, nature, arts, museums, shopping, nightlife
- **Available hours per day**: Hours available for activities (e.g., 8 AM - 6 PM, full day, half day)
- **Transportation mode**: At least one mode selected: own car, rental car, Kingston Transit only, walking only, or mixed
- **Pace preference**: How user wants to experience Kingston (relaxed, moderate, or packed schedule)

**Important Optional Inputs (improve itinerary quality):**

- Group composition (solo, couple, family with kids, friend group, number of people)
- Dietary restrictions (vegetarian, vegan, gluten-free, allergies)
- Accessibility needs (wheelchair access, limited walking distance, mobility concerns)
- Weather sensitivity (willing to do outdoor activities in rain/cold, or prefer indoor-only)
- Specific venues user wants to include or avoid

**Less Critical Optional Inputs (nice-to-have):**

- Meal preferences (casual vs. fine dining, local specialties)
- Photography priorities (scenic photo opportunities)
- Shopping preferences
- Evening activities interest (bars, live music, quiet dining)


### Conversation Flow Design

**Step 1: Opening \& Context Setting**

- Greet user and explain the trip planner purpose
- Ask if planning a first-time visit or return trip to Kingston
- Determine trip timeframe (specific dates or planning ahead for season/month)

**Step 2: Core Constraint Collection (Required)**

**Starting Location Question (REQUIRED):**

- **Primary Question**: "Where will you be staying or starting from in Kingston?"
- **Purpose**: Essential for calculating optimal routing and building itinerary from user's actual location
- **Accepted Formats**:
    - **Specific address**: "123 Princess Street, Kingston" or "455 Princess St"
    - **Hotel/Accommodation name**: "Holiday Inn Kingston Waterfront", "Queen's University area Airbnb"
    - **Landmark**: "Kingston Airport", "VIA Rail Station", "Bus Terminal", "Kingston Train Station"
    - **General area**: "Downtown Kingston", "Queen's University area", "Near Fort Henry", "Waterfront district"
- **Clarification Examples**:
    - If user says "hotel": Ask "Which hotel or what area of Kingston?"
    - If user says "Airbnb": Ask "Do you know the address or which neighborhood? (e.g., downtown, waterfront, university area)"
    - If user says "haven't booked yet": Ask "Which area are you considering? (downtown, waterfront, near highway for easy access)"
    - If user says "arriving by plane/train/bus": Ask "Will you stay near the airport/station, or move to a different area?"
- **Validation**:
    - Must provide at least general area/neighborhood (required field)
    - Verify location is within Kingston, Ontario area
    - Use Google Maps Geocoding API to validate and get coordinates
    - Store both raw user input and geocoded coordinates
    - **Block if**: No location provided: "I need to know your starting location to plan efficient routes and minimize travel time."
- **Default Handling**:
    - If truly unknown, default to "Downtown Kingston (King St \& Princess St intersection)" as central starting point
    - Notify user: "I'll use downtown Kingston as your starting point. You can update this later."

**Why Starting Location is Critical:**

1. **First Activity Optimization**: Choose first activity that's accessible from starting location (avoid 45-minute drive to first stop)
2. **Route Efficiency**: Build circular or efficient route that minimizes backtracking
3. **Daily Start/End**: Plan itinerary to start and end each day near accommodation
4. **Transportation Realism**: Calculate actual travel times from accommodation to first venue
5. **Parking/Transit Access**: If user staying in downtown hotel, prioritize walking/transit; if near highway, consider car-based routing
6. **Return Logistics**: Ensure user can easily return to accommodation at end of each day

**Dates/Duration Question (REQUIRED):**

- **Primary Question**: "When are you planning to visit Kingston?"
- **Required Format**:
    - **Option A**: Exact dates → "Please provide your start date and end date (e.g., March 15, 2026 to March 17, 2026)"
    - **Option B**: Planning ahead → "Which season or month? (e.g., Summer 2026, August 2026, Fall 2026)"
- **Validation**:
    - If exact dates: both start AND end date must be provided
    - Start date must be today or future date
    - End date must be after start date
    - Duration must be ≥ 1 day and ≤ 30 days
    - **Block if**: Only one date provided or no dates: "I need both your start date AND end date to plan your trip."
    - If season/month only: note that exact itinerary will need dates closer to trip

**Budget Question (REQUIRED):**

- **Primary Question**: "What's your budget for the Kingston trip?"
- **Clarification**: "This should include meals, activities, and transportation (we'll help allocate it)"
- **Required Format**: Dollar amount as total budget OR daily budget
- **Minimum Daily Budget**: \$50 per day (for two meals and activities)
- **Validation**:
    - If total budget provided: calculate daily = total ÷ duration
    - If daily budget provided: calculate total = daily × duration
    - **Reject if**: daily budget < \$50 (respond: "A minimum of \$50 per day is needed to cover two meals and activities in Kingston. Please adjust your budget or trip duration.")
    - **Warn if**: daily budget \$50-70 (respond: "Your budget of \$X per day is tight. We'll focus on affordable options and free attractions.")
    - **Confirm if**: daily budget ≥ \$70 (respond: "Great! \$X per day gives us good flexibility for meals and activities.")

**Interests Question (REQUIRED):**

- **Primary Question**: "What activities interest you most in Kingston?"
- **Options Provided**: history, food, waterfront, nature, arts, museums, shopping, nightlife
- **Required**: At least ONE category must be selected
- **Optimal**: 2-4 categories for balanced itinerary
- **Validation**:
    - **Block if**: No interests selected: "Please select at least one interest category so we can personalize your itinerary."
    - If >6 interests selected: "That's a lot! Let's prioritize your top 3-4 interests for a more focused experience."

**Time Available Question (REQUIRED):**

- **Primary Question**: "How many hours per day do you want for activities?"
- **Options**: "Full day (8-10 hours)", "Most of day (6-8 hours)", "Half day (4-6 hours)", "Just a few hours (2-4 hours)", or specific hours like "9 AM to 6 PM"
- **Validation**: Must be between 2-12 hours per day
- **Block if**: No time specified: "I need to know how much time you have each day to plan your itinerary."

**Transportation Question (REQUIRED):**

- **Primary Question**: "How will you get around Kingston?"
- **Options**: "I have my own car", "I'll rent a car", "Kingston Transit (bus)", "Walking only", "Mix of transit and walking"
- **Required**: At least one mode must be selected
- **Cross-reference with starting location**: If airport/bus terminal, suggest rental car or transit
- **Validation**:
    - **Block if**: No mode selected: "Please choose at least one way you'll get around Kingston."
    - If "own car" or "rental car": note that parking info and costs will be included
    - If "walking only" and starting from airport: **Warn**: "Walking from the airport to downtown is ~10km. Consider transit or car rental."

**Pace Preference Question (REQUIRED - NEW):**

- **Primary Question**: "What pace would you like for your Kingston trip?"
- **Options \& Descriptions**:
    - **Relaxed**: "Take it easy, 2-3 activities per day with plenty of time at each, leisurely meals, no rushing"
    - **Moderate**: "Balanced pace, 4-5 activities per day, reasonable time at each venue, standard meal times"
    - **Packed**: "See as much as possible, 6+ activities per day, shorter visits, quick meals, maximize experiences"
- **Why This is Critical**:
    - Determines number of activities per day
    - Affects time allocation at each venue (relaxed = 90-120 min, moderate = 60-90 min, packed = 30-60 min)
    - Influences meal timing (relaxed = 90-min dinners, packed = 45-min quick meals)
    - Impacts buffer time between activities (relaxed = 20-min buffer, packed = 5-min buffer)
    - Affects itinerary feasibility validation (packed pace has higher risk of delays)
- **Validation**:
    - **Block if**: No pace selected: "Please tell me if you prefer a relaxed, moderate, or packed schedule so I can plan the right amount of activities."
    - **Cross-check with time available**:
        - If pace = "packed" but hours_per_day < 6: **Warn**: "A packed schedule typically needs 8+ hours per day. Consider 'moderate' pace for your available time."
        - If pace = "relaxed" but hours_per_day > 10: **Info**: "With 10+ hours available, you have plenty of time for a truly relaxed experience."
- **Impact on Itinerary**:
    - **Relaxed pace**: 2-3 activities/day, longer meals (90+ min lunch, 120+ min dinner), extended time at key venues, built-in rest periods
    - **Moderate pace**: 4-5 activities/day, standard meals (60 min lunch, 90 min dinner), typical venue visit times, reasonable buffers
    - **Packed pace**: 6+ activities/day, quick meals (45 min lunch, 60 min dinner), shorter venue visits, minimal downtime, tighter schedule

**Step 3: Enhancement Information (Optional but Valuable)**

**Group Type:** "Are you traveling solo, with family, or with friends?"

- Options: solo, couple, family (ask number and ages of children), friend group (ask size)

**Dietary Needs:** "Any dietary restrictions or preferences we should know about?"

- Common options: vegetarian, vegan, gluten-free, dairy-free, nut allergies, shellfish allergies

**Accessibility:** "Do you have any mobility or accessibility needs?"

- Options: wheelchair access required, limited walking distance, prefer minimal stairs, no special needs

**Weather Tolerance:** "Are you comfortable with outdoor activities in any weather?"

- Options: "Yes, any weather is fine", "Prefer indoor backup options if it rains", "Indoor activities only"

**Step 4: Validation \& Confirmation**

**Display Summary:**

```
Let me confirm your Kingston trip details:

📍 Starting Location: Holiday Inn Kingston Waterfront (245 Ontario St)
📅 Dates: March 15-17, 2026 (3 days)
💰 Budget: $200 total ($67 per day)
❤️ Interests: history, waterfront, food
⏰ Daily Time: 8 hours per day (9 AM - 5 PM)
🚗 Transportation: Own car
⚡ Pace: Moderate (4-5 activities per day)
👥 Group: Couple (2 people)
🍽️ Dietary: Vegetarian
♿ Accessibility: No special needs
☀️ Weather: Prefer indoor backups if rainy

Your itinerary will:
- Start and end each day near your hotel
- Include 4-5 activities per day at a comfortable pace
- Allocate ~60-90 minutes per activity
- Include driving times and parking info
- Stay within your $67/day budget

Does this look correct?
```

**Validation Checks Before Confirmation:**

- ✅ Starting location provided (address, hotel, or general area)
- ✅ Start date AND end date provided (or season/month for advance planning)
- ✅ Budget ≥ \$50 per day
- ✅ At least 1 interest category selected
- ✅ Transportation mode selected
- ✅ Time per day specified
- ✅ Pace preference selected (relaxed/moderate/packed)

**Critical Validation Warnings:**

- ⚠️ **Location-Transportation Mismatch**: If starting location is "Kingston Airport" but transportation is "walking only" → warn: "Walking from the airport may be impractical. Consider transit or car rental."
- ⚠️ **Low Budget Warning**: If daily budget \$50-70: "Your budget is tight. We'll prioritize affordable dining and include free attractions."
- ⚠️ **Limited Time Warning**: If hours per day < 6: "With only [X] hours per day, we'll focus on must-see attractions and minimize travel time."
- ⚠️ **Pace-Time Mismatch**:
    - If pace = "packed" but hours_per_day < 6: "A packed pace typically needs 8+ hours. Consider 'moderate' pace for your available time."
    - If pace = "relaxed" but hours_per_day < 4: "With only [X] hours available, even a relaxed pace will be limited to 1-2 activities per day."
- ⚠️ **Contradictions**: Check for conflicts and prompt user to resolve:
    - "Packed schedule" + "only 4 hours/day" → "These don't match. Would you like to extend your daily hours or choose a more relaxed pace?"
    - "Relaxed pace" + "8 interests selected" → "A relaxed pace won't cover all 8 interests in [X] days. Should we prioritize your top 3-4?"

**Step 5: Readiness Assessment**

**Calculate Completeness Score:**

- All 7 critical inputs present = 100% ready
- Missing pace preference = 85% ready (can default to "moderate" but quality suffers)
- Missing transportation mode = 80% ready (can default to mixed mode)
- Missing starting location = 70% ready (can default to downtown but routing suboptimal)
- Missing time per day = 70% ready (can default to 8 hours)
- Missing interests = 40% ready (cannot generate quality itinerary - BLOCK)
- Missing budget = 30% ready (cannot validate feasibility - BLOCK)
- Missing dates = 20% ready (cannot check venue availability - BLOCK for exact dates, ALLOW for season/month but note limitations)

**Proceed Conditions:**

- **Score 100%**: ✅ Proceed immediately to itinerary generation
- **Score 85-99%**: ✅ Proceed with noted defaults: "I'll use [default value] for [missing field]. You can adjust later."
- **Score < 85%**: ❌ Block and request missing critical information: "I need [missing fields] to create your itinerary."


### Handling Ambiguous Inputs

**Vague Starting Location Responses:**

User says: "a hotel" or "Airbnb"
→ Ask: "Which hotel or what neighborhood in Kingston? (e.g., downtown waterfront, near Queen's University, near Highway 401)"

User says: "downtown"
→ Confirm: "Downtown Kingston works! I'll use the King St and Princess St area as your central starting point."

User says: "don't know yet"
→ Respond: "No problem! For now, I'll plan around downtown Kingston (most central). You can update your starting location once you book accommodation, and I'll re-optimize your route."

User says: "arriving by plane/train"
→ Ask: "After you arrive at the airport/station, where will you be staying? Or should I plan activities starting from the airport/station?"

**Vague Budget Responses:**

User says: "cheap" or "budget-friendly"
→ Ask: "To plan effectively, would 'budget-friendly' mean under \$50/day, \$50-75/day, or \$75-100/day?"
→ Validate: Enforce minimum \$50/day

User says: "money is not an issue"
→ Suggest: "Great! For planning purposes, should we estimate \$150/day, \$200/day, or higher?"

User provides total budget without specifying dates:
→ Respond: "I see \$200 budget. How many days is your trip? This helps me calculate your daily budget."

User provides budget below \$50/day:
→ **Reject**: "A minimum of \$50 per day is needed for two meals and activities in Kingston. Your current budget of \$X per day is below this. Would you like to increase your budget or shorten your trip?"

**Unclear Time Constraints:**

User says: "a few days"
→ Ask: "To create an accurate itinerary, I need exact dates. What are your start and end dates? Or if planning ahead, which month or season?"

User says: "maybe 2-3 days"
→ Ask: "Should I plan for 2 days or 3 days? Or provide your exact start and end dates?"

User says: "flexible schedule"
→ Ask: "That's great! What are your earliest start date and latest end date? Or if you haven't decided yet, which season or month are you considering?"

User provides only month/season (no exact dates):
→ Accept: "Got it - planning for [August 2026]. Note that I'll create a general itinerary, but you'll need to confirm exact dates later to check venue availability and book reservations."
→ Flag: Mark trip as "advance_planning" with season/month stored
→ Limitation: Cannot validate specific opening hours, cannot check real-time weather, cannot book activities

User provides start date only (no end date):
→ **Block**: "I need both your start date AND end date to plan your trip. When will your Kingston trip end?"

**Generic Interest Statements:**

User says: "everything" or "open to anything"
→ Respond: "Let's prioritize to create a focused experience! Which THREE appeal most: history/museums, food/dining, outdoor/nature, shopping, waterfront, nightlife?"

User says: "sightseeing"
→ Probe: "What kind of sights? Are you more interested in: historical landmarks, natural scenery, architectural buildings, or local neighborhoods?"

User says: "just show me the popular stuff"
→ Respond: "Kingston's popular for history (Fort Henry), waterfront (Lake Ontario), and food scene. Which of these interests you most?"

User provides NO interests:
→ **Block**: "I need to know at least one thing you're interested in (history, food, nature, etc.) to create a personalized itinerary. What would you like to experience in Kingston?"

**Unclear Transportation:**

User says: "whatever works"
→ Clarify: "Do you have access to a car, or should I plan using Kingston Transit buses and walking?"

User says: "maybe rent a car"
→ Ask: "Should I plan assuming you'll have a car (more flexibility, includes parking costs), or provide transit/walking options?"

User says: "not sure yet"
→ Default: "I'll create an itinerary with multiple transportation options (car, transit, walking) so you can choose later."

**Vague Pace Preference:**

User says: "normal" or "regular"
→ Interpret as: "moderate" pace and confirm: "I'll plan a moderate pace with 4-5 activities per day. Does that sound right?"

User says: "I want to see everything"
→ Clarify: "That sounds like a packed schedule! Just confirming - are you comfortable with 6+ activities per day with shorter visits at each place?"

User says: "not too busy" or "take our time"
→ Interpret as: "relaxed" pace and confirm: "I'll plan a relaxed pace with 2-3 activities per day and plenty of time at each. Sound good?"

User says: "efficient but not rushed"
→ Interpret as: "moderate" pace and confirm: "That's a moderate pace - balanced activities with reasonable time at each venue."

### Data Completeness Thresholds

**Minimum Viable Inputs (required to proceed):**

- **Starting location**: Address, hotel name, or at least general Kingston area
- **Dates**: Exact start date AND end date (YYYY-MM-DD), OR season/month for advance planning
- **Budget**: Dollar amount with minimum \$50 per day
- **Interests**: At least 1 category selected
- **Transportation**: At least one mode selected
- **Time Available**: Hours per day (can default to 8 hours if not specified)
- **Pace Preference**: Relaxed, moderate, or packed (can default to "moderate" if not specified but quality suffers)

**Optimal Inputs (enables high-quality generation):**

- All minimum viable inputs ✅
- Group type specified
- Dietary restrictions noted
- Accessibility needs documented
- Weather tolerance indicated

**Advanced Inputs (for exceptional personalization):**

- Specific venues user wants to include
- Venues user wants to avoid
- Meal preferences (casual vs. fine dining)
- Photography priorities
- Shopping interests
- Evening activity preferences

***

## Phase 2: Data Extraction \& MongoDB Architecture

### Natural Language to Structured Data

**Extraction Strategy Using Gemini:**

- Send user's conversational responses to Gemini with extraction prompt
- Request structured JSON output matching MongoDB schema
- Validate extracted data for completeness and format
- Handle low-confidence extractions by asking user to confirm

**Extraction Prompt Template:**

```
User provided the following information about their Kingston trip:
[USER RESPONSES]

Extract structured trip planning data in JSON format:
{
  "starting_location": {
    "raw_input": "string" (what user provided),
    "address": "string or null",
    "landmark_type": "hotel/airbnb/airport/train_station/bus_terminal/general_area/null",
    "area": "downtown/waterfront/university/highway/null",
    "coordinates": {"latitude": number or null, "longitude": number or null}
  },
  "trip_dates": {
    "start_date": "YYYY-MM-DD" (required),
    "end_date": "YYYY-MM-DD" (required),
    "season_month": "string or null" (if planning ahead: "Summer 2026", "August 2026", etc.)
  },
  "budget": {
    "total": number (required),
    "daily": number (required, minimum 50)
  },
  "interests": [array of strings from: history, food, waterfront, nature, arts, museums, shopping, nightlife] (required, minimum 1),
  "hours_per_day": number (default 8 if not specified),
  "transportation_mode": [array from: own_car, rental_car, transit, walking] (required, minimum 1),
  "pace_preference": "relaxed/moderate/packed" (REQUIRED),
  "group": {"type": "solo/couple/family/group", "size": number, "children": boolean},
  "dietary_restrictions": [array of strings],
  "accessibility_needs": [array of strings],
  "weather_sensitivity": "high/moderate/low"
}

Validation rules:
- starting_location.raw_input: required
- trip_dates: start_date AND end_date both required (or season_month for advance planning)
- budget.daily: must be >= 50
- interests: must have at least 1 item
- transportation_mode: must have at least 1 item
- pace_preference: must be one of "relaxed", "moderate", or "packed" (REQUIRED)

If any required field is missing or invalid, set to null and flag for clarification.
Return only valid JSON.
```


### MongoDB Collections Schema Design

**Collection 1: `user_trip_requests`**
Purpose: Store all collected user constraints and preferences

```
Document Structure:
{
  "_id": ObjectId,
  "user_id": string (generated UUID),
  "created_at": ISODate,
  "status": string (enum: "collecting", "complete", "generating", "active"),
  "starting_location": {
    "raw_input": string (what user provided),
    "formatted_address": string (geocoded full address),
    "landmark_name": string or null (e.g., "Holiday Inn Waterfront"),
    "landmark_type": string (enum: "hotel", "airbnb", "airport", "train_station", "bus_terminal", "general_area"),
    "area": string (enum: "downtown", "waterfront", "university", "highway", "north", "west"),
    "coordinates": {
      "latitude": number,
      "longitude": number
    },
    "geocoded": boolean (true if validated via Google Maps API),
    "notes": string or null (e.g., "Default to downtown - user hasn't booked yet")
  },
  "trip_dates": {
    "start_date": "YYYY-MM-DD" (REQUIRED),
    "end_date": "YYYY-MM-DD" (REQUIRED),
    "duration_days": number,
    "season_month": string or null (for advance planning: "Summer 2026", "August 2026")
  },
  "budget": {
    "total": number (dollars, REQUIRED),
    "daily_limit": number (REQUIRED, minimum 50),
    "categories": {
      "food": number,
      "activities": number,
      "transport": number
    }
  },
  "interests": [array of strings] (REQUIRED, minimum 1 item),
  "time_constraints": {
    "hours_per_day": number (default 8),
    "start_hour": string ("09:00"),
    "end_hour": string ("18:00")
  },
  "transportation": {
    "modes": [array: "own_car", "rental_car", "transit", "walking"] (REQUIRED, minimum 1),
    "primary_mode": string
  },
  "pace_preference": string (enum: "relaxed", "moderate", "packed") (REQUIRED),
  "pace_details": {
    "activities_per_day": number (relaxed: 2-3, moderate: 4-5, packed: 6+),
    "avg_time_per_activity_minutes": number (relaxed: 90-120, moderate: 60-90, packed: 30-60),
    "meal_duration_minutes": {"lunch": number, "dinner": number},
    "buffer_between_activities_minutes": number (relaxed: 20, moderate: 15, packed: 5)
  },
  "group_details": {
    "type": string (enum: "solo", "couple", "family", "group"),
    "size": number,
    "has_children": boolean,
    "children_ages": [array of numbers]
  },
  "dietary_restrictions": [array of strings],
  "accessibility_needs": [array of strings],
  "weather_sensitivity": string (enum: "high", "moderate", "low")
}
```

**Collection 2: `kingston_venues`**
Purpose: Master database of all Kingston attractions, restaurants, and points of interest

```
Document Structure:
{
  "_id": ObjectId,
  "venue_id": string (unique identifier),
  "name": string,
  "category": string (enum: "historical_site", "museum", "restaurant", "park", "waterfront", "shopping", "entertainment", "arts"),
  "subcategory": string,
  "description": string (brief description),
  "coordinates": {
    "latitude": number,
    "longitude": number
  },
  "address": string,
  "distance_from_downtown_km": number (for routing optimization),
  "opening_hours": {
    "monday": {"open": "HH:MM", "close": "HH:MM", "closed": boolean},
    "tuesday": {...},
    // ... all days of week
    "seasonal_closure": {
      "active": boolean,
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD"
    }
  },
  "pricing": {
    "admission": number (0 for free venues),
    "adult": number,
    "senior": number,
    "child": number,
    "family_pass": number
  },
  "typical_visit_duration_minutes": number,
  "visit_duration_by_pace": {
    "relaxed": number (e.g., 120 minutes),
    "moderate": number (e.g., 90 minutes),
    "packed": number (e.g., 60 minutes)
  },
  "indoor_outdoor": string (enum: "indoor", "outdoor", "mixed"),
  "weather_dependent": boolean,
  "accessibility": {
    "wheelchair_accessible": boolean,
    "elevator": boolean,
    "accessible_parking": boolean,
    "accessible_restroom": boolean
  },
  "dietary_options": [array: "vegetarian", "vegan", "gluten_free"] (for restaurants),
  "transportation_notes": {
    "parking_available": boolean,
    "parking_cost": number,
    "transit_accessible": boolean,
    "nearest_bus_routes": [array of route numbers],
    "walkable_from_downtown": boolean (< 2km)
  },
  "website": string (URL),
  "last_updated": ISODate
}
```

**Collection 3: `trip_active_itineraries`**
Purpose: Store generated itineraries with real-time execution tracking

```
Document Structure:
{
  "_id": ObjectId,
  "trip_id": string (references user_trip_requests),
  "user_id": string,
  "generated_at": ISODate,
  "status": string (enum: "draft", "confirmed", "active", "completed"),
  "starting_location": {
    "address": string,
    "coordinates": {"latitude": number, "longitude": number}
  },
  "pace": string (enum: "relaxed", "moderate", "packed"),
  "total_estimated_cost": number,
  "days": [
    {
      "day_number": 1,
      "date": "YYYY-MM-DD",
      "starts_from_accommodation": boolean (true for first activity each day),
      "ends_at_accommodation": boolean (true for last activity each day),
      "activities": [
        {
          "sequence": 1,
          "venue_id": string (references kingston_venues),
          "venue_name": string,
          "category": string,
          "time_start": "HH:MM",
          "time_end": "HH:MM",
          "duration_minutes": number,
          "pace_adjusted_duration": number (actual time based on pace preference),
          "cost": number,
          "indoor_outdoor": string,
          "execution_status": string (enum: "upcoming", "in_progress", "completed", "skipped"),
          "actual_start_time": "HH:MM" (null until started),
          "actual_end_time": "HH:MM" (null until completed),
          "distance_from_starting_location_km": number,
          "transportation_to_next": {
            "mode": string,
            "duration_minutes": number,
            "distance_km": number,
            "cost": number,
            "route_details": string,
            "google_maps_link": string,
            "buffer_time_minutes": number (based on pace: relaxed=20, moderate=15, packed=5)
          }
        }
      ],
      "return_to_accommodation": {
        "mode": string,
        "duration_minutes": number,
        "distance_km": number,
        "estimated_arrival_time": "HH:MM",
        "google_maps_link": string
      },
      "day_total_cost": number,
      "total_duration_hours": number,
      "activities_count": number
    }
  ],
  "adaptation_log": [
    {
      "timestamp": ISODate,
      "trigger": string (enum: "weather_change", "user_running_late", "user_skipped_activity", "budget_exceeded", "pace_adjustment"),
      "changes_made": string (description),
      "affected_activities": [array of venue_ids]
    }
  ],
  "weather_warnings": [
    {
      "day": number,
      "time": string,
      "warning": string,
      "affected_activities": [array]
    }
  ]
}
```

**Collection 4: `trip_budget_state`**
Purpose: Real-time budget tracking and spending monitoring

```
Document Structure:
{
  "_id": ObjectId,
  "trip_id": string,
  "user_id": string,
  "budget_allocation": {
    "total": number,
    "food": {"allocated": number, "spent": number, "remaining": number},
    "activities": {"allocated": number, "spent": number, "remaining": number},
    "transport": {"allocated": number, "spent": number, "remaining": number}
  },
  "daily_budget": number (minimum 50),
  "spending_log": [
    {
      "timestamp": ISODate,
      "category": string,
      "amount": number,
      "description": string,
      "venue_id": string
    }
  ],
  "current_status": {
    "total_spent": number,
    "total_remaining": number,
    "days_remaining": number,
    "projected_total": number,
    "overspend_risk": boolean
  },
  "alerts": [
    {
      "timestamp": ISODate,
      "severity": string (enum: "info", "warning", "critical"),
      "message": string,
      "category": string
    }
  ],
  "last_updated": ISODate
}
```

**Collection 5: `scraped_venue_data`**
Purpose: Store raw scraped content and change detection

```
Document Structure:
{
  "_id": ObjectId,
  "venue_id": string (references kingston_venues),
  "venue_name": string,
  "website_url": string,
  "scrape_timestamp": ISODate,
  "content_hash": string (SHA-256 hash of normalized extracted data),
  "previous_content_hash": string (hash from previous scrape),
  "change_detected": boolean,
  "extracted_data": {
    "hours": string (raw text),
    "pricing": string (raw text),
    "special_events": string,
    "seasonal_info": string,
    "closure_notices": string
  },
  "parsing_status": {
    "success": boolean,
    "errors": [array of error messages]
  }
}
```

**Collection 6: `venue_change_alerts`**
Purpose: Track detected changes from web scraping

```
Document Structure:
{
  "_id": ObjectId,
  "venue_id": string,
  "venue_name": string,
  "change_detected_at": ISODate,
  "change_type": string (enum: "hours_changed", "pricing_changed", "closure_notice", "event_added", "seasonal_update"),
  "severity": string (enum: "minor", "major", "critical"),
  "old_value": string,
  "new_value": string,
  "affected_trips": [
    {
      "trip_id": string,
      "user_id": string,
      "notification_sent": boolean
    }
  ],
  "resolution_status": string (enum: "pending", "users_notified", "itineraries_updated", "resolved")
}
```

**Collection 7: `kingston_weather_forecast`**
Purpose: Store weather forecasts for itinerary planning

```
Document Structure:
{
  "_id": ObjectId,
  "date": "YYYY-MM-DD",
  "location": "Kingston, ON",
  "hourly_forecast": [
    {
      "hour": number (0-23),
      "temperature_celsius": number,
      "conditions": string (enum: "sunny", "partly_cloudy", "cloudy", "rain", "snow", "thunderstorm"),
      "precipitation_probability": number (0-100),
      "precipitation_amount_mm": number,
      "wind_speed_kmh": number,
      "feels_like_celsius": number,
      "outdoor_activity_suitable": boolean
    }
  ],
  "daily_summary": {
    "high_temp": number,
    "low_temp": number,
    "conditions": string,
    "rain_probability": number
  },
  "fetched_at": ISODate,
  "source": string (API name)
}
```


### Data Validation Rules

**Starting Location Validation:**

- Must provide at least general area/neighborhood
- If specific address: validate via Google Maps Geocoding API
- If landmark (hotel/airport): verify it exists in Kingston
- Store coordinates for routing calculations
- **Block if**: No location provided at all

**Trip Dates Validation:**

- Start date must be today or future date
- End date must be after start date
- Duration must be ≥ 1 day and ≤ 30 days (reasonable trip length)
- **Block if**: Only one date provided or no dates

**Budget Validation:**

- Total budget must be > 0
- **Daily budget MUST BE ≥ \$50** (for two meals and activities)
- **Reject if daily budget < \$50**: "Minimum \$50 per day required for two meals and activities"
- **Warn if daily budget \$50-70**: "Budget is tight, will prioritize affordable options"
- Category allocations must sum to ≤ total budget
- Suggested allocation: ~40% food, ~45% activities, ~15% transport

**Interest Validation:**

- **Must select at least 1 interest category** (required field)
- **Reject if no interests provided**: "Please select at least one interest to personalize your itinerary"
- **Optimal: 2-4 categories** for balanced itinerary
- Maximum 6 interest categories (focus the itinerary)

**Pace Preference Validation:**

- **Must select one of: relaxed, moderate, or packed** (required field)
- **Block if**: No pace selected
- **Cross-validation with time available**:
    - If pace = "packed" but hours_per_day < 6: **Warn** and suggest "moderate"
    - If pace = "relaxed" but hours_per_day < 4: **Warn** about limited activities possible
    - If pace = "packed" and hours_per_day ≥ 10: **Confirm** user ready for intensive schedule
- **Set pace parameters**:
    - Relaxed: 2-3 activities/day, 90-120 min/activity, 20-min buffers, 90+ min meals
    - Moderate: 4-5 activities/day, 60-90 min/activity, 15-min buffers, 60-90 min meals
    - Packed: 6+ activities/day, 30-60 min/activity, 5-min buffers, 45-60 min meals

**Transportation Validation:**

- Must select at least one transportation mode
- If "transit" selected, verify Kingston Transit operates on trip dates (no service on certain holidays)
- If "walking" only and accessibility needs = wheelchair, flag potential conflict
- **Cross-validation with starting location**:
    - Airport + walking only: **Warn** about distance
    - Downtown hotel + own car: **Info** about parking costs and availability

**Group Validation:**

- If group type = "family" and children ages provided, verify venues are age-appropriate
- Group size must be 1-20 (reasonable range)

***

## Phase 3: Itinerary Generation \& Real-Time Adaptation

[Continues with Phase 3 content - same as previous version with additions for starting location optimization and pace-based timing]

### Step 1: Pre-Generation Data Assembly

**Data Retrieval Process:**

1. **Process Starting Location:**
    - Geocode user's starting location if not already done
    - Store coordinates as "home base" for routing
    - Calculate distance from starting location to all venues in database
    - Prioritize venues within reasonable first-stop distance (≤15 min travel from starting location)
2. **Fetch Relevant Venues from MongoDB:**
    - Query `kingston_venues` where category matches user interests
    - Filter out venues closed during trip dates (check seasonal_closure)
    - Filter out venues incompatible with accessibility needs
    - Sort by relevance score AND distance from starting location
    - Apply pace-specific filtering:
        - **Relaxed pace**: Prioritize venues with longer recommended visit times (90+ min)
        - **Moderate pace**: Include mix of short and long visit venues
        - **Packed pace**: Include quick-visit venues (30-60 min) and multiple nearby options
    - Limit to top 50-100 venues to avoid overwhelming Gemini
3. **Retrieve Weather Forecast:**
    - Query `kingston_weather_forecast` for exact trip dates
    - If forecast not available (trip too far in future), use historical average
    - Flag days with high rain probability (>60%) or extreme temperatures
4. **Load Transportation Data:**
    - If user selected "transit", load Kingston Transit routes from `kingston_transit_routes`
    - Calculate which bus routes serve starting location area
    - If user selected "own_car" or "rental_car", note parking availability at venues
    - Calculate approximate travel times between venue pairs AND from starting location (Google Maps Distance Matrix API or pre-calculated matrix)
5. **Calculate Budget Allocation:**
    - Divide total budget across trip days
    - Allocate budget by category: ~40% food, ~45% activities, ~15% transport (adjust based on transportation mode)
    - Adjust meal budget by pace:
        - **Relaxed**: Higher meal budget (leisurely dining)
        - **Moderate**: Standard meal budget
        - **Packed**: Lower meal budget (quick eats)
    - Set per-activity budget limits

### Step 2: Gemini API Itinerary Generation

**Prompt Engineering Strategy:**

```
You are a Kingston, Ontario trip planning expert. Generate a detailed, feasible itinerary based on the following constraints:

**Trip Details:**
- Starting Location: [address/hotel/area] at coordinates ([lat], [lng])
- Dates: [start_date] to [end_date] ([duration] days)
- Daily Time Available: [hours_per_day] hours per day
- Budget: $[total_budget] total ($[daily_budget] per day) - MINIMUM $50/day for two meals + activities
- Transportation: [mode]
- Pace: [relaxed/moderate/packed]

**Pace-Specific Requirements:**
[If RELAXED]:
- 2-3 activities per day maximum
- Allocate 90-120 minutes per activity (extended time to fully experience each venue)
- Include 90-minute lunch breaks and 120-minute dinner experiences
- Build in 20-minute buffers between activities for relaxed transitions
- Avoid back-to-back activities - include rest periods

[If MODERATE]:
- 4-5 activities per day
- Allocate 60-90 minutes per activity (standard visit times)
- Include 60-minute lunch breaks and 90-minute dinners
- Build in 15-minute buffers between activities
- Balanced pacing with reasonable downtime

[If PACKED]:
- 6+ activities per day
- Allocate 30-60 minutes per activity (efficient visits)
- Include 45-minute lunch breaks and 60-minute dinners
- Build in 5-minute buffers between activities
- Maximize experiences, minimize downtime
- Group nearby venues together to reduce travel time

**User Preferences:**
- Interests: [comma-separated interests] (at least 1 required)
- Group: [group_type, size]
- Dietary Restrictions: [restrictions]
- Weather Sensitivity: [sensitivity level]

**Available Venues (Kingston, ON):**
[JSON array of 30-50 relevant venues with: name, category, hours, pricing, duration by pace, indoor/outdoor, coordinates, distance from starting location]

**Weather Forecast:**
[Daily weather summary for trip dates]

**Critical Requirements:**
1. FIRST ACTIVITY each day must be accessible from starting location ([address])
2. LAST ACTIVITY each day must allow easy return to starting location
3. Calculate and include travel time FROM starting location to first venue
4. Calculate and include travel time FROM last venue BACK to starting location
5. Optimize route to minimize backtracking (circular/efficient routing from home base)
6. Each day must fit within [hours_per_day] hours INCLUDING travel to/from starting location
7. Stay within budget ($[daily_budget] per day, minimum $50/day)
8. Follow pace-specific timing requirements for [pace] pace
9. Include TWO MEALS per day minimum (budget accounts for this)
10. Include venue name, start time, end time, estimated cost for each activity
11. Account for travel time between activities
12. Avoid scheduling outdoor activities during forecasted rain
13. Ensure venues are open during scheduled times (check operating hours)
14. Match activities to user interests

**Routing Strategy:**
- Prefer venues closer to starting location for first/last activities of day
- Group nearby venues together to reduce travel time
- Consider circular routes that naturally return toward starting location
- If using transit, ensure bus routes connect starting location to venues

**Output Format (JSON):**
{
  "itinerary_options": [
    {
      "option_name": "[Pace]-Paced Kingston Explorer",
      "total_cost": number,
      "activities_per_day_avg": number,
      "total_travel_time_hours": number,
      "days": [
        {
          "day": 1,
          "date": "YYYY-MM-DD",
          "morning_departure": {
            "time": "HH:MM",
            "from": "starting_location",
            "to": "first_venue",
            "travel_minutes": number,
            "mode": "car/transit/walk"
          },
          "activities": [
            {
              "time_start": "09:00",
              "time_end": "11:00",
              "venue_name": "Fort Henry",
              "venue_id": "fort_henry_001",
              "category": "historical_site",
              "cost": 20,
              "duration_reason": "Relaxed pace allows full fort tour + reenactment",
              "notes": "Historical tour of 19th century fort"
            }
          ],
          "evening_return": {
            "time": "HH:MM",
            "from": "last_venue",
            "to": "starting_location",
            "travel_minutes": number,
            "mode": "car/transit/walk"
          }
        }
      ]
    }
  ]
}
```

[Continue with remaining sections from Phase 3: Feasibility Validation, Multi-Modal Transportation Planning, Real-Time Weather Adaptation, Real-Time Budget Tracking, Real-Time Schedule Adaptation, and Apache Airflow Web Scraping - same as previous version]

***

## Team Work Distribution (3 Developers, 14 Days)

**Developer 1: User Interface \& Data Collection**

- Days 1-4: Build conversational UI and input validation
- Days 5-8: Gemini API integration for data extraction and itinerary generation
- Days 9-14: Integration testing, user flow polish, demo preparation

**Developer 2: MongoDB \& Core Logic**

- Days 1-2: MongoDB setup, schema design, data seeding (20-30 venues)
- Days 3-6: Feasibility validation logic, budget tracking, pace-based timing calculations
- Days 7-10: Real-time adaptation engines (weather, budget, schedule)
- Days 11-14: Testing, bug fixes, optimization

**Developer 3: APIs \& Web Scraping**

- Days 1-3: Google Maps API integration, routing, geocoding
- Days 4-6: Weather API integration, outdoor activity detection
- Days 7-8: Multi-modal transportation logic
- Days 9-12: Web scraping scripts, change detection implementation
- Days 13-14: Integration testing, demo scenarios

**Daily Standups**: 15-minute sync each morning to coordinate integration points

***

## MVP Success Criteria \& Testing

[Same testing scenarios as previous version, plus:]

**Test Case: Starting Location Routing**

- Input: Starting location: "Holiday Inn Waterfront", 2-day trip, \$150 budget, interests: history, moderate pace, own car
- Expected: First activity close to hotel (<10 min drive), last activity allows easy return, circular route with minimal backtracking
- Verify: Morning departure and evening return times calculated, total daily hours fit within limit

**Test Case: Pace Preference Impact**

- Input A: Relaxed pace, 8 hours/day
- Input B: Packed pace, 8 hours/day
- Expected: Relaxed generates 2-3 activities with 90-120 min each; Packed generates 6+ activities with 30-60 min each
- Verify: Timing matches pace parameters, buffer times differ (relaxed=20min, packed=5min)

***

## Estimated Development Timeline (14 Days, 3 Developers)

**Days 1-2: Foundation Setup (All Developers)**

- MongoDB installation, database and collections creation
- Schema design and implementation
- Manual venue data seeding (20-30 Kingston venues with complete data including pace-specific durations)
- Google Maps API and Weather API key setup
- Create sample user trips for testing

**Days 3-4: Core Workflows (Split Work)**

- Dev 1: Conversational UI with all 7 required inputs including starting location and pace
- Dev 2: Data validation logic, pace parameter calculations
- Dev 3: Google Maps geocoding integration for starting location validation

**Days 5-6: Itinerary Generation (Split Work)**

- Dev 1: Gemini API integration, prompt engineering with starting location and pace parameters
- Dev 2: Feasibility validator with pace-aware timing checks
- Dev 3: Multi-modal transportation planning, route optimization from home base

**Days 7-8: Real-Time Features Part 1 (Split Work)**

- Dev 1: Budget tracking UI and alerts
- Dev 2: Weather adaptation engine
- Dev 3: Transportation routing with starting location integration

**Days 9-10: Real-Time Features Part 2 (Split Work)**

- Dev 1: Schedule adaptation with pace-aware re-optimization
- Dev 2: Budget rebalancing logic
- Dev 3: Web scraping scripts for 10 venues

**Days 11-12: Change Detection \& Polish (Split Work)**

- Dev 1: User flow testing and refinement
- Dev 2: Content hashing and change detection logic
- Dev 3: Alert generation for venue changes

**Day 13: Integration \& Testing (All Developers)**

- Full end-to-end integration testing
- Test all pace variations
- Test starting location routing
- Bug fixes

**Day 14: Demo Preparation (All Developers)**

- Prepare demo script showcasing all 7 mandatory features
- Record backup demo video
- Final rehearsal
- Prepare presentation materials

***

This updated prompt now includes **starting location** and **pace preference** as critical required inputs, with comprehensive validation, routing optimization, and pace-specific timing throughout the entire system. The team structure for 3 developers is clearly defined with distributed responsibilities.

