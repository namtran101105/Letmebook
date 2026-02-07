# 🚀 Quick Start Guide - Kingston Trip Planner Chatbot

## Step 1: Install Dependencies

```bash
cd travel-planner/backend
pip install -r requirements.txt
```

## Step 2: Get Groq API Key

1. Visit [Groq Console](https://console.groq.com/keys)
2. Sign in (create account if needed)
3. Click "Create API Key"
4. Copy your API key (starts with `gsk_...`)

## Step 3: Configure Environment

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
# GROQ_API_KEY=gsk_your_actual_key_here
```

## Step 4: Run the Application

```bash
python app.py
```

You should see:
```
✅ Settings validated
📍 Using Groq model: llama-3.3-70b-versatile
🌐 Starting server on http://0.0.0.0:5000
```

## Step 5: Open the Chatbot UI

Open your browser and go to:
```
http://localhost:5000
```

## 🎯 How to Use

1. **Type a message** describing your Kingston trip, for example:
   - "I want to visit Kingston next weekend with my family of 4. We love history and food tours. Budget is $500-800."
   - "Planning a solo trip July 15-20, interested in museums and hiking, vegetarian"

2. **See extracted preferences** in the right panel showing:
   - Trip dates and duration
   - Budget range
   - Interests and activities
   - Group information
   - Special requirements
   - Validation status

3. **Refine preferences** by sending more messages:
   - "Actually, I want to see Fort Henry and try local wines"
   - The system will update your preferences with new information

## 📁 Project Structure

```
travel-planner/
├── backend/
│   ├── app.py                      # Flask server (RUN THIS)
│   ├── .env                        # Your API key (create this)
│   ├── .env.example                # Template
│   ├── requirements.txt            # Dependencies
│   ├── services/
│   │   └── nlp_extraction_service.py   # AI extraction logic
│   ├── clients/
│   │   └── groq_client.py          # Groq API client
│   ├── models/
│   │   └── trip_preferences.py     # Data structure
│   └── config/
│       └── settings.py             # Configuration
└── frontend/
    └── index.html                  # Chatbot UI
```

## 🔧 Troubleshooting

### Error: "GROQ_API_KEY environment variable is required"
- Make sure you created `.env` file in `backend/` directory
- Check that your API key is correctly added to `.env`

### Error: "Cannot connect to server"
- Make sure `python app.py` is running
- Check that no other service is using port 5000

### Error: "Package not installed"
- Run `pip install -r requirements.txt` again
- Make sure you're in the `backend/` directory

## 🎨 What Each Component Does

### Backend (app.py)
- **`/api/extract`** - Extracts preferences from first user message
- **`/api/refine`** - Updates preferences with additional information
- **`/api/health`** - Checks if service is running

### Frontend (index.html)
- **Chat Panel** - Where you type messages
- **Results Panel** - Shows extracted preferences in real-time
- **Auto-refinement** - Automatically uses refinement for follow-up messages

### NLP Service
- Uses **Groq API** with **Llama 3.3 70B** model
- Extracts structured data from natural language
- Validates and scores completeness

## 📊 Example Conversation

```
You: I want to visit Kingston next weekend with my family of 4.
     We love history and food tours. Budget is around $500-800.

Bot: ✅ I've extracted your preferences! Check the panel on the right for details.

[Right Panel Shows:]
- Group Size: 4 people
- Traveling With: family
- Interests: history, food tours
- Budget: $500-$800 CAD
- Completeness: 67%

You: Actually, I'm vegetarian and want to see Fort Henry

Bot: ✅ I've extracted your preferences! Check the panel on the right for details.

[Right Panel Updates:]
- Dietary Restrictions: vegetarian
- Must See: Fort Henry
- Completeness: 78%
```

## 🚀 Next Steps

Once the extraction is working, you can:
1. Add itinerary generation service
2. Save preferences to JSON files (using storage layer)
3. Build trip scheduling features
4. Add more UI features

---

**Need help?** Check the console output for error messages or validation warnings.
