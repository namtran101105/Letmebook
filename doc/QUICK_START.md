# Quick Start Guide - Kingston Trip Planner

## 🎯 You're All Set!

Your system is configured and ready to use with **Gemini API** (primary).

---

## 🚀 3 Ways to Use the Services

### 1. Web Interface (Easiest)

Start the server and use the chatbot:

```bash
python backend/app.py
```

Then open: **http://localhost:8000**

**Try this in the chat:**
```
I want to visit Kingston from May 10-12, 2026.
Budget is $900. Love museums, food, and waterfront.
Moderate pace, downtown location.
```

---

### 2. Demo Scripts (Recommended for Learning)

#### NLP Extraction Demo

```bash
python demo_nlp_extraction.py
```

Shows 3 examples:
- ✅ Complete trip extraction
- ⚠️ Incomplete extraction + refinement
- 💬 Conversational response generation

#### Itinerary Generation Demo

```bash
python demo_itinerary_generation.py
```

Generates two complete itineraries:
- 🏛️ 3-day moderate trip ($900)
- 🌊 5-day relaxed trip ($1500)

**⏱️ Note:** Itinerary generation takes 30-60 seconds

---

### 3. API Calls (For Integration)

#### NLP Extraction API

```bash
# Extract preferences
curl -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Kingston May 10-12, $900, museums and food, moderate pace, downtown"
  }' | python -m json.tool
```

#### Health Check

```bash
curl http://localhost:8000/api/health | python -m json.tool
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Kingston Trip Planner",
  "primary_llm": "gemini",
  "model": "Gemini (gemini-2.0-flash)",
  "nlp_service_ready": true,
  "error": null
}
```

---

## 📝 Required Information (10 Fields)

To generate an itinerary, you need:

1. **city** - Kingston
2. **country** - Canada
3. **start_date** - YYYY-MM-DD
4. **end_date** - YYYY-MM-DD
5. **duration_days** - Must match date range
6. **budget** - Minimum $50/day
7. **budget_currency** - CAD
8. **interests** - At least 1 (history, food, museums, waterfront, nature, arts, shopping, nightlife)
9. **pace** - relaxed, moderate, or packed
10. **location_preference** - downtown, near nature, waterfront, etc.

---

## 🎨 Pace Options

### Relaxed (Chill)
- 2-3 activities per day
- 90-120 minutes per activity
- Long meals and breaks
- Perfect for leisurely exploration

### Moderate (Balanced)
- 4-5 activities per day
- 60-90 minutes per activity
- Good balance of activities and rest
- Most popular choice

### Packed (Intense)
- 6-8 activities per day
- 30-60 minutes per activity
- Quick meals and short breaks
- See everything!

---

## 💰 Budget Guidelines

**Minimum:** $50/day
- $30-40 for meals (lunch + dinner)
- $10-20 for activities

**Recommended:**
- **Relaxed:** $100-150/day
- **Moderate:** $70-100/day
- **Packed:** $60-80/day

---

## 🔍 What's Working

### ✅ Phase 1 Complete
- NLP extraction from natural language
- Preference validation
- Web chatbot interface
- Conversational responses
- Preference refinement

### ✅ Phase 2 Complete
- Itinerary generation (Gemini API)
- Day-by-day timetables
- Activity scheduling
- Meal planning
- Budget tracking
- Feasibility validation

### ⏳ Next Steps
- Add itinerary endpoint to Flask API
- MongoDB integration
- Google Maps API for real venues
- Weather API integration
- Frontend itinerary display

---

## 🐛 Troubleshooting

### Server won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill the process if needed
kill -9 <PID>
```

### API errors (500)
```bash
# Check your API keys
cat backend/.env | grep GEMINI_KEY

# Verify service initialization
python diagnose.py
```

### Missing dependencies
```bash
pip install "groq>=0.13.0" "httpx>=0.27.0" google-genai flask flask-cors python-dotenv python-dateutil
```

---

## 📚 Full Documentation

- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Complete guide with all examples
- **[CLAUDE.md](CLAUDE.md)** - Project context and architecture
- **[backend/.env.example](backend/.env.example)** - Configuration template

---

## 🎯 Quick Test

Try this right now:

```bash
# Terminal 1: Start server
python backend/app.py

# Terminal 2: Test NLP extraction
python demo_nlp_extraction.py

# Terminal 3: Test itinerary generation
python demo_itinerary_generation.py
```

---

## ✨ Example End-to-End

```python
import requests
import asyncio
import sys
sys.path.insert(0, 'backend')
from services.itinerary_service import ItineraryService

# Step 1: Extract preferences
response = requests.post('http://localhost:8000/api/extract', json={
    'user_input': 'Kingston May 10-12, $900, museums and food, moderate pace, downtown'
})

preferences = response.json()['preferences']
print(f"Extracted: {preferences['city']}, {preferences['start_date']} to {preferences['end_date']}")

# Step 2: Generate itinerary
async def generate():
    service = ItineraryService()
    itinerary = await service.generate_itinerary(preferences, "example-001")
    print(f"Generated {len(itinerary.days)}-day itinerary with {itinerary.total_activities} activities!")
    return itinerary

itinerary = asyncio.run(generate())
```

---

## 🌟 Current Status

✅ **System is ready!**
- Using Gemini API (gemini-2.0-flash)
- All dependencies installed
- Both services working

**Your API Keys:**
- Gemini: Configured ✅
- Groq: Configured ✅ (fallback)

**Start using it:**
```bash
python backend/app.py
```

Then open http://localhost:8000 and start chatting!

---

**Last Updated:** February 7, 2026
**Status:** ✅ Ready to Use
