# Testing Itinerary Generation with Airflow Venue Database

This guide shows you how to test the complete itinerary generation workflow with real venue data from the Airflow PostgreSQL database.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Database Setup](#database-setup)
3. [Verify Database Connection](#verify-database-connection)
4. [Seed Venue Data](#seed-venue-data)
5. [Test Itinerary Generation](#test-itinerary-generation)
6. [Verify Venue Integration](#verify-venue-integration)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Docker and Docker Compose
You need Docker Desktop installed and running with `docker compose` available. Verify with:
```bash
docker --version
docker compose version
```

### 2. Environment Variables
Ensure your `backend/.env` file has:
```bash
# Gemini API
GEMINI_KEY=your_gemini_api_key

# Database (Docker Compose - note port 5435 to avoid conflicts)
APP_DB_URL=postgresql+psycopg2://app:app@localhost:5435/app

# Default city
DEFAULT_CITY=Toronto
DEFAULT_COUNTRY=Canada
```

### 3. Install Python Dependencies
```bash
cd /Users/vietbui/Desktop/gia_version/MonVoyage
source .venv/bin/activate  # or create one: python -m venv .venv
pip install -r requirements.txt
```

---

## Database Setup

### Step 1: Start Docker Services

From the repository root, start all services (Airflow, PostgreSQL, Chroma):

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Verify containers are running:
```bash
docker compose -f docker-compose.dev.yml ps
```

You should see containers like:
- `airflow-webserver`
- `airflow-scheduler`
- `airflow-postgres`
- `appdb` (this is the database we'll use)
- `chroma`

### Step 2: Create Airflow Admin User

Airflow doesn't create users automatically. Create one with:

```bash
docker compose -f docker-compose.dev.yml exec airflow-webserver bash -lc '
airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com
'
```

### Step 3: Verify Database Connection

Check the database is accessible:

```bash
docker compose -f docker-compose.dev.yml exec appdb psql -U app -d app -c "\dt"
```

**Expected Output:**
```
              List of relations
 Schema |      Name       | Type  | Owner 
--------+-----------------+-------+-------
 public | change_events   | table | app
 public | page_snapshots  | table | app
 public | place_facts     | table | app
 public | places          | table | app
 public | tracked_pages   | table | app
```

If tables don't exist yet, they will be created when you seed the database.

---

## Seed Venue Data

### Step 2: Initialize Database Tables and Seed Toronto Venues

```bash
cd /Users/vietbui/Desktop/gia_version/MonVoyage

# Run the seeding script
python airflow/dags/lib/seed_tracked_sites.py
```

**Expected Output:**
```4: Initialize Database Tables and Seed Toronto Venues

Run the seeding script inside the Airflow container:

```bash
docker compose -f docker-compose.dev.yml exec airflow-webserver bash -lc \
  "python /opt/airflow/dags/lib/seed_tracked_sites.py"
```

**Expected Output:**
```
Seeding database with Toronto venues...
✅ Created 15 places
✅ Created 15 tracked pages
✅ Database seeded successfully!
```

### Step 5: Verify Venues Were Seeded

Check the database directly:

```bash
docker compose -f docker-compose.dev.yml exec appdb psql -U app -d app
```

Then run these SQL queries:

```sql
-- Check places
SELECT id, place_key, canonical_name, category
FROM places;

-- Check tracked pages
SELECT id, place_id, url, page_type, extract_strategy, enabled
FROM tracked_pages;

-- Exit psql
\q
```

Or create a test script to query venues:

```bash
cat > backend/tests
    service = VenueService()
    
    # Test 1: Query Toronto venues for Culture and History
    print("Test 1: Culture and History venues in Toronto")
    print("-" * 60)
    venues = service.get_venues_for_itinerary(
        city="Toronto",
        interests=["Culture and History"],
        budget_per_day=100.0
    )
    
    print(f"Found {len(venues)} venues:")
    for v in venues[:5]:  # Show first 5
        print(f"  - {v['name']} ({v.get('category', 'N/A')})")
        print(f"    Address: {v.get('address', 'N/A')}")
    
    print("\n" + "="*60 + "\n")
    
    # Test 2: Query for Food and Beverage
    print("Test 2: Food and Beverage venues in Toronto")
    print("-" * 60)
    venues = service.get_venues_for_itinerary(
        city="Toronto",
        interests=["Food and Beverage"],
        budget_per_day=150.0
    )
    
    print(f"Found {len(venues)} venues:")
    for v in venues:
        print(f"  - {v['name']} ({v.get('category', 'N/A')})")
    
    print("\n" + "="*60 + "\n")
    
# Run the test
    # Test 3: Query for multiple interests
    print("Test 3: Multiple interests (Culture + Food + Natural Place)")
    print("-" * 60)
    venues = service.get_venues_for_itinerary(
        city="Toronto",
        interests=["Culture and History", "Food and Beverage", "Natural Place"],
        budget_per_day=200.0
    )
    
    print(f"Found {len(venues)} venues:")
    categories = {}
    for v in venues:
        cat = v.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\nBreakdown by category:")
    for cat, count in sorted(categories.items()):
        print(f"  - {cat}: {count}")

if __name__ == "__main__":
    test_6enue_query()
EOF

python3 backend/tests/test_venue_query.py
```

**Expected Output:**
```
Test 1: Culture and History venues in Toronto
------------------------------------------------------------
Found 6 venues:
  - CN Tower (tourism)
    Address: 290 Bremner Blvd, Toronto, ON M5V 3L9
  - Royal Ontario Museum (museum)
    Address: 100 Queens Park, Toronto, ON M5S 2C6
  - Casa Loma (culture)
    Address: 1 Austin Terrace, Toronto, ON M5R 1X8
  ...
```

---

## Test Itinerary Generation

### Step 4: Create a Complete Test Script

```bash
cat > test_itinerary_with_db.py << 'EOF'
"""
Complete test of itinerary generation with Airflow database venues.
Demonstrates that venues from the DB are used in the generated itinerary.
"""
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.itinerary_service import ItineraryService
from utils.id_generator import generate_trip_id

async def test_itinerary_with_venues():
    """Generate itinerary and verify venues come from database."""
    
    print("="*80)
    print("ITINERARY GENERATION TEST WITH AIRFLOW VENUE DATABASE")
    print("="*80)
    print()
    
    # Sample trip preferences (all required fields)
    preferences = {
        # Location
        "city": "Toronto",
        "country": "Canada",
        "location_preference": "downtown",
        
        # Dates (3-day trip)
        "start_date": "2026-03-15",
        "end_date": "2026-03-17",
        "duration_days": 3,
        
        # Budget
        "budget": 300.0,  # $100/day
        "budget_currency": "CAD",
        
        # Preferences
        "interests": ["Culture and History", "Food and Beverage"],
        "pace": "moderate",
        
        # Optional fields
        "starting_location": "Downtown Toronto",
        "hours_per_day": 8,
        "transportation_modes": ["transit", "walking"],
    }
    
    print("📋 Trip Preferences:")
    print(f"   Destination: {preferences['city']}, {preferences['country']}")
    print(f"   Dates: {preferences['start_date']} to {preferences['end_date']}")
    print(f"   Duration: {preferences['duration_days']} days")
    print(f"   Budget: ${preferences['budget']} {preferences['budget_currency']} (${preferences['budget']/preferences['duration_days']:.2f}/day)")
    print(f"   Interests: {', '.join(preferences['interests'])}")
    print(f"   Pace: {preferences['pace']}")
    print()
    
    # Initialize service
    print("🔧 Initializing ItineraryService...")
    service = ItineraryService()
    request_id = generate_trip_id()
    print(f"   Request ID: {request_id}")
    print()
    
    # Generate itinerary
    print("🚀 Generating itinerary (this may take 10-20 seconds)...")
    print()
    
    try:
        itinerary = await service.generate_itinerary(
            preferences=preferences,
            request_id=request_id
        )
        
        print("✅ Itinerary generated successfully!")
        print()
        print("="*80)
        print("ITINERARY DETAILS")
        print("="*80)
        print()
        
        # Summary
        print(f"Option Name: {itinerary.option_name}")
        print(f"Total Cost: ${itinerary.total_cost:.2f} CAD")
        print(f"Activities per Day (avg): {itinerary.activities_per_day_avg:.1f}")
        print(f"Total Travel Time: {itinerary.total_travel_time_hours:.1f} hours")
        print(f"Number of Days: {len(itinerary.days)}")
        print()
        
        # Count activities from database
        total_activities = 0
        db_activities = 0
        
        for day in itinerary.days:
            total_activities += len(day.activities)
            db_activities += sum(1 for a in day.activities if a.from_database)
        
        print("📊 DATABASE VENUE USAGE:")
        print(f"   Total activities: {total_activities}")
        print(f"   From database: {db_activities}")
        print(f"   Generated by AI: {total_activities - db_activities}")
        print(f"   Database coverage: {(db_activities/total_activities*100):.1f}%")
        print()
        
        # Day-by-day breakdown
        for day in itinerary.days:
            print("="*80)
            print(f"DAY {day.day} - {day.date}")
            print("="*80)
            print()
            
            # Morning departure
            if day.morning_departure:
                print(f"🚗 Morning Departure ({day.morning_departure.time}):")
                print(f"   From: {day.morning_departure.from_location}")
                print(f"   To: {day.morning_departure.to_location}")
                print(f"   Duration: {day.morning_departure.travel_minutes} min ({day.morning_departure.mode})")
                print()
            
            # Activities
            print(f"🎯 Activities ({len(day.activities)}):")
            for i, activity in enumerate(day.activities, 1):
                db_flag = "🗄️  [DB]" if activity.from_database else "🤖 [AI]"
                print(f"\n   {i}. {db_flag} {activity.venue_name}")
                print(f"      Time: {activity.planned_start} - {activity.planned_end}")
                print(f"      Category: {activity.category or 'N/A'}")
                print(f"      Cost: ${activity.estimated_cost:.2f}")
                if activity.notes:
                    print(f"      Notes: {activity.notes}")
                if activity.duration_reason:
                    print(f"      Duration: {activity.duration_reason}")
            
            print()
            
            # Meals
            print(f"🍽️  Meals ({len(day.meals)}):")
            for meal in day.meals:
                print(f"   - {meal.meal_type.title()} at {meal.venue_name} ({meal.time}) - ${meal.cost:.2f}")
            
            print()
            
            # Evening return
            if day.evening_return:
                print(f"🏠 Evening Return ({day.evening_return.time}):")
                print(f"   From: {day.evening_return.from_location}")
                print(f"   To: {day.evening_return.to_location}")
                print(f"   Duration: {day.evening_return.travel_minutes} min ({day.evening_return.mode})")
            
            print()
            print(f"💰 Budget: ${day.daily_budget_spent:.2f} / ${day.daily_budget_allocated:.2f}")
            print()
        
        # Save to file
        output_file = f"itinerary_trip_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(itinerary.to_dict(), f, indent=2)
        
        print("="*80)
        print(f"✅ Itinerary saved to: {output_file}")
        print("="*80)
        
        # Verification summary
        print()
        print("🔍 VERIFICATION CHECKLIST:")
        checks = [
            ("Days match duration", len(itinerary.days) == preferences['duration_days']),
            ("Budget within limits", itinerary.total_cost <= preferences['budget']),
            ("Activities per day > 0", all(len(d.activities) > 0 for d in itinerary.days)),
            ("All days have meals", all(len(d.meals) >= 2 for d in itinerary.days)),
            ("DB venues used", db_activities > 0),
            ("Interests covered", len(itinerary.days) > 0),
        ]
        
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"   {status} {check_name}")
        
        print()
        
        return itinerary
        
    except Exception as e:
        print(f"❌ Error generating itinerary: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_itinerary_with_venues())
EOF

python test/test_itinerary_with_db.py
```

**Expected Output:**
```
================================================================================
ITINERARY GENERATION TEST WITH AIRFLOW VENUE DATABASE
================================================================================

📋 Trip Preferences:
   Destination: Toronto, Canada
   Dates: 2026-03-15 to 2026-03-17
   Duration: 3 days
   Budget: $300.0 CAD ($100.00/day)
   Interests: Culture and History, Food and Beverage
   Pace: moderate

🔧 Initializing ItineraryService...
   Request ID: TRIP-20260207-abc123

🚀 Generating itinerary (this may take 10-20 seconds)...

✅ Itinerary generated successfully!

================================================================================
ITINERARY DETAILS
================================================================================

Option Name: Toronto Cultural & Culinary Explorer
Total Cost: $285.00 CAD
Activities per Day (avg): 4.3
Total Travel Time: 2.5 hours
Number of Days: 3

📊 DATABASE VENUE USAGE:
   Total activities: 13
   From database: 9
   Generated by AI: 4
   Database coverage: 69.2%

================================================================================
DAY 1 - 2026-03-15
================================================================================

🚗 Morning Departure (09:00):
   From: Downtown Toronto
   To: Royal Ontario Museum
   Duration: 15 min (transit)

🎯 Activities (4):

   1. 🗄️  [DB] Royal Ontario Museum
      Time: 09:30 - 11:00
      Category: Culture and History
      Cost: $25.00
      Notes: Explore Canada's largest museum with world cultures and natural history
      Duration: 90 minutes allows thorough exploration at moderate pace

   2. 🗄️  [DB] St. Lawrence Market
      Time: 11:30 - 12:30
      Category: Food and Beverage
      Cost: $15.00
      Notes: Browse local vendors and sample fresh foods
      Duration: 60 minutes for leisurely market exploration

   ...
```

---

## Verify Venue Integration

### Step 5: Check Database Integration Points

**Verify venues are marked correctly:**

```python
# In the test output, look for:
# 🗄️  [DB] = Venue from Airflow database (from_database=True)
# 🤖 [AI] = Venue generated by Gemini AI (from_database=False)
```

**Check the JSON output file:**

```bash
# Open the generated JSON file
cat itinerary_trip_*.json | python -m json.tool | grep -A 5 "from_database"
```

**Expected:**
```json
"activities": [
  {
    "activity_id": "act-001",
    "venue_name": "Royal Ontario Museum",
    "from_database": true,
    ...
  }
]
```

### Step 6: Inspect Database Logs

```bash
cat > backend/test_venue_fetch_log.py << 'EOF'
"""Test that shows exactly what happens during venue fetching."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.itinerary_service import ItineraryService

async def test_venue_fetch():
    service = ItineraryService()
    
    preferences = {
        "city": "Toronto",
        "interests": ["Culture and History", "Food and Beverage"],
        "budget": 300.0,
        "duration_days": 3,
    }
    
    print("Fetching venues for Toronto with interests: Culture and History, Food and Beverage")
    print("-" * 80)
    
    venues = await service._fetch_venues(preferences)
    
    print(f"\n✅ Fetched {len(venues)} venues from database:\n")
    
    for v in venues:
        print(f"   - {v['name']}")
        print(f"     Category: {v.get('category', 'N/A')}")
        print(f"     Address: {v.get('address', 'N/A')}")
        print()

if __name__ == "__main__":
    asyncio.run(test_venue_fetch())
EOF

python backend/tests/test_venue_fetch_log.py
```

---

## Troubleshooting

### Issue 1: No venues returned

**Symptom:**
```
Found 0 venues from database
Database coverage: 0.0%
```

**Solutions:**
```bash
# 1. Check if Docker containers are running
docker compose -f docker-compose.dev.yml ps

# 2. Verify database tables exist
docker compose -f docker-compose.dev.yml exec appdb psql -U app -d app -c "\dt"

# 3. Re-run seeding script
docker compose -f docker-compose.dev.yml exec airflow-webserver bash -lc \
  "python /opt/airflow/dags/lib/seed_tracked_sites.py"

# 4. Verify data in database
docker compose -f docker-compose.dev.yml exec appdb psql -U app -d app -c \
  "SELECT canonical_name, city, category FROM places;"
```

### Issue 2: Database connection refused

**Symptom:**
```
❌ Connection failed: connection refused
```

**Solutions:**
```bash
# 1. Check if containers are running
docker compose -f docker-compose.dev.yml ps

# 2. Start all services if not running
docker compose -f docker-compose.dev.yml up -d

# 3. Check logs for the appdb container
docker compose -f docker-compose.dev.yml logs appdb

# 4. Verify port mapping (should be 5435:5432)
docker compose -f docker-compose.dev.yml ps appdb

# 5. Update .env to use correct port
# APP_DB_URL=postgresql+psycopg2://app:app@localhost:5435/app
```

### Issue 3: Venues not matching interests

**Symptom:**
All activities show `🤖 [AI]` instead of `🗄️  [DB]`

**Solutions:**
```bash
# Check interest-to-category mapping
cat > check_mapping.py << 'EOF'
from backend.services.venue_service import INTEREST_TO_DB_CATEGORIES
import json
print(json.dumps(INTEREST_TO_DB_CATEGORIES, indent=2))
EOF

python check_mapping.py

# Verify venue categories in DB
docker compose -f docker-compose.dev.yml exec appdb psql -U app -d app -c \
  "SELECT DISTINCT category FROM places;"
```

### Issue 4: Gemini API errors

**Symptom:**
```
google.api_core.exceptions.PermissionDenied
```

**Solutions:**
```bash
# Check API key
grep GEMINI_KEY backend/.env

# Verify key works
python backend/diagnose.py
```

---

## Success Criteria

Your test is successful if:

✅ **Database Connection:** `test_db_connection.py` shows all 5 tables  
✅ **Venues Seeded:** At least 10-15 venues in the database  
✅ **Venues Queried:** `test_venue_query.py` returns venues for each interest  
✅ **Itinerary Generated:** Complete 3-day itinerary with activities and meals  
✅ **Database Integration:** At least 50% of activities have `from_database: true`  
✅ **Budget Feasible:** Total cost ≤ budget specified  
✅ **All Days Have Meals:** Each day has lunch AND dinner  

---

## Next Steps

After successful testing:

1. **Access Airflow UI** to monitor the data pipeline:
   ```bash
   # Open http://localhost:8080
   # Login: admin / admin
   # Enable and trigger the website_change_monitor DAG
   ```

2. **Add More Venues** by editing `airflow/dags/lib/seed_tracked_sites.py` and re-running:
   ```bash
   docker compose -f docker-compose.dev.yml exec airflow-webserver bash -lc \
     "python /opt/airflow/dags/lib/seed_tracked_sites.py"
   ```

3. **Test Other Cities** by seeding venues for different cities

4. **Integrate into Frontend** - Call `/api/generate-itinerary` endpoint

5. **Add New Features** - Weather, budget estimation, bookings

---

## Quick Reference Commands

```bash
# Start all services
docker compose -f docker-compose.dev.yml up -d --build

# Stop all services
docker compose -f docker-compose.dev.yml down

# View logs
docker compose -f docker-compose.dev.yml logs -f appdb
docker compose -f docker-compose.dev.yml logs -f airflow-webserver

# Database inspection
docker compose -f docker-compose.dev.yml exec appdb psql -U app -d app -c \
  "SELECT * FROM places LIMIT 5;"

docker compose -f docker-compose.dev.yml exec appdb psql -U app -d app -c \
  "SELECT COUNT(*) FROM places WHERE city ILIKE '%toronto%';"

# Check existing tables
docker compose -f docker-compose.dev.yml exec appdb psql -U app -d app -c "\dt"

# Clean database (start fresh)
docker compose -f docker-compose.dev.yml exec appdb psql -U app -d app -c \
  "DROP TABLE IF EXISTS change_events, page_snapshots, place_facts, tracked_pages, places CASCADE;"

# Re-seed after cleaning
docker compose -f docker-compose.dev.yml exec airflow-webserver bash -lc \
  "python /opt/airflow/dags/lib/seed_tracked_sites.py"

# Full test sequence (from host machine)
python backend/tests/test_venue_query.py
python backend/tests/test_venue_fetch_log.py
python test/test_itinerary_with_db.py
```

---

**Date:** February 7, 2026  
**Version:** 1.0  
**Author:** MonVoyage Team
