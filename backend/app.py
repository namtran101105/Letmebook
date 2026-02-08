"""
FastAPI application for MonVoyage Trip Planner.
Handles NLP extraction, itinerary generation, weather, and booking workflows.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys
import os
import uuid
import uvicorn

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from services.nlp_extraction_service import NLPExtractionService
from services.itinerary_service import ItineraryService
from services.weather_service import WeatherService
from services.booking_service import BookingService
from models.trip_preferences import TripPreferences
from config.settings import settings

# Initialize FastAPI app
app = FastAPI(
    title="MonVoyage Trip Planner",
    description="API for travel planning with NLP extraction and itinerary generation",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize NLP service at startup
nlp_service = None
nlp_service_error = None

try:
    nlp_service = NLPExtractionService()
    print("✅ NLP Extraction Service initialized successfully")
except Exception as e:
    nlp_service_error = str(e)
    print(f"❌ Failed to initialize NLP service: {e}")
    import traceback
    traceback.print_exc()


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------

class ExtractRequest(BaseModel):
    user_input: str


class RefineRequest(BaseModel):
    preferences: Dict[str, Any]
    additional_input: str
    last_question: Optional[str] = None  # conversation phase context for yes/no answers


class GenerateItineraryRequest(BaseModel):
    preferences: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    service: str
    model: str
    nlp_service_ready: bool
    error: Optional[str] = None


class TripResponse(BaseModel):
    success: bool
    preferences: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    bot_message: Optional[str] = None
    saved_to_file: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get('/')
async def index():
    """Serve the frontend HTML page."""
    frontend_path = os.path.join(os.path.dirname(__file__), '../frontend/index.html')
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.get('/api/health', response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'service': 'MonVoyage Trip Planner',
        'model': settings.GROQ_MODEL,
        'nlp_service_ready': nlp_service is not None,
        'error': nlp_service_error if nlp_service_error else None
    }


@app.post('/api/extract', response_model=TripResponse)
async def extract_preferences(request: ExtractRequest):
    """
    Extract trip preferences from user input (first message in conversation).
    """
    if not nlp_service:
        raise HTTPException(
            status_code=500,
            detail='NLP service not initialized. Check your API keys in .env file'
        )

    try:
        user_input = request.user_input.strip()
        if not user_input:
            raise HTTPException(status_code=400, detail='user_input is required')

        # Extract preferences
        preferences = await nlp_service.extract_preferences(user_input)

        # Validate preferences
        validation = nlp_service.validate_preferences(preferences)

        # Generate conversational response
        bot_message, all_questions_asked = await nlp_service.generate_conversational_response(
            user_input=user_input,
            preferences=preferences,
            validation=validation,
            is_refinement=False
        )

        # Save to file when all questions answered
        saved_file_path = None
        if all_questions_asked:
            saved_file_path = nlp_service.save_preferences_to_file(preferences)

        response_data = {
            'success': True,
            'preferences': preferences.to_dict(),
            'validation': validation,
            'bot_message': bot_message
        }
        if saved_file_path:
            response_data['saved_to_file'] = saved_file_path

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/refine', response_model=TripResponse)
async def refine_preferences(request: RefineRequest):
    """
    Refine existing preferences with additional user input (follow-up messages).
    Accepts optional last_question to provide context for yes/no answers.
    """
    if not nlp_service:
        raise HTTPException(status_code=500, detail='NLP service not initialized')

    try:
        preferences_dict = request.preferences
        additional_input = request.additional_input.strip()

        if not preferences_dict or not additional_input:
            raise HTTPException(
                status_code=400,
                detail='preferences and additional_input are required'
            )

        # Convert dict to TripPreferences object
        existing_preferences = TripPreferences.from_dict(preferences_dict)

        # Refine preferences (pass last_question context for yes/no interpretation)
        refined = await nlp_service.refine_preferences(
            existing_preferences,
            additional_input,
            last_question=request.last_question
        )

        # Validate
        validation = nlp_service.validate_preferences(refined)

        # Generate conversational response
        bot_message, all_questions_asked = await nlp_service.generate_conversational_response(
            user_input=additional_input,
            preferences=refined,
            validation=validation,
            is_refinement=True
        )

        # Save to file when all questions answered
        saved_file_path = None
        if all_questions_asked:
            saved_file_path = nlp_service.save_preferences_to_file(refined)

        response_data = {
            'success': True,
            'preferences': refined.to_dict(),
            'validation': validation,
            'bot_message': bot_message
        }
        if saved_file_path:
            response_data['saved_to_file'] = saved_file_path

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/generate-itinerary')
async def generate_itinerary(request: GenerateItineraryRequest):
    """
    Full itinerary generation workflow:
    1. Fetch related venue links from Airflow DB via ItineraryService
    2. Get weather forecast for trip dates via WeatherService
    3. Trigger BookingService for flight link (if needs_flight=True)
    4. Trigger BookingService for Airbnb link (if needs_airbnb=True)
    5. Generate complete AI itinerary with venues from DB, 2 meals/day, pace-based activities
    """
    try:
        preferences_dict = request.preferences
        request_id = str(uuid.uuid4())[:8]

        print(f"\n🚀 Starting itinerary generation [req-{request_id}]")
        print(f"   City: {preferences_dict.get('city')}, Country: {preferences_dict.get('country')}")
        print(f"   Dates: {preferences_dict.get('start_date')} → {preferences_dict.get('end_date')}")
        print(f"   Pace: {preferences_dict.get('pace')}")
        print(f"   Needs flight: {preferences_dict.get('needs_flight')}, Needs Airbnb: {preferences_dict.get('needs_airbnb')}")

        # Convert to TripPreferences for weather and booking services
        prefs_obj = TripPreferences.from_dict(preferences_dict)

        # --- Step 1 & 5: Generate itinerary (fetches venues from Airflow DB internally) ---
        print(f"\n[1] Generating itinerary with venue data from Airflow DB...")
        itinerary_svc = ItineraryService()
        itinerary = await itinerary_svc.generate_itinerary(preferences_dict, request_id)
        print(f"   ✅ Itinerary generated: {len(itinerary.days)} days, {itinerary.total_activities} activities")

        # --- Step 2: Get weather forecast ---
        print(f"\n[2] Fetching weather forecast...")
        weather_result = {"forecasts": [], "error": None}
        try:
            weather_svc = WeatherService()
            weather_result = weather_svc.get_trip_weather(prefs_obj)
            if weather_result.get("error"):
                print(f"   ⚠️  Weather unavailable: {weather_result['error']}")
            else:
                print(f"   ✅ Weather fetched: {len(weather_result.get('forecasts', []))} days")
        except Exception as e:
            print(f"   ⚠️  Weather service error: {e}")
            weather_result["error"] = str(e)

        # --- Steps 3 & 4: Booking links ---
        booking_result = {"accommodation": None, "transportation": None, "skipped": True}
        if prefs_obj.needs_flight or prefs_obj.needs_airbnb:
            print(f"\n[3] Generating booking links...")
            try:
                booking_svc = BookingService()
                booking_result = booking_svc.book_trip(prefs_obj)
                if prefs_obj.needs_flight:
                    trans = booking_result.get("transportation", {})
                    if trans and not trans.get("error"):
                        print(f"   ✅ Flight link generated")
                    else:
                        print(f"   ⚠️  Flight booking issue: {trans.get('error') if trans else 'unknown'}")
                if prefs_obj.needs_airbnb:
                    accom = booking_result.get("accommodation", {})
                    if accom and not accom.get("error"):
                        print(f"   ✅ Airbnb link generated")
                    else:
                        print(f"   ⚠️  Airbnb booking issue: {accom.get('error') if accom else 'unknown'}")
            except Exception as e:
                print(f"   ⚠️  Booking service error: {e}")
                booking_result["error"] = str(e)
        else:
            print(f"\n[3] No bookings requested — skipping")

        print(f"\n✅ Itinerary generation complete [req-{request_id}]")

        return {
            "success": True,
            "itinerary": itinerary.to_dict(),
            "weather": weather_result,
            "booking": booking_result,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/weather')
async def get_weather(city: str, country: str = "", start_date: str = "", end_date: str = ""):
    """Get weather forecast for a city and date range."""
    if not city or not start_date or not end_date:
        raise HTTPException(status_code=400, detail='city, start_date, and end_date are required')

    try:
        prefs = TripPreferences(
            city=city,
            country=country or "",
            start_date=start_date,
            end_date=end_date,
            interests=[],
            pace="moderate",
        )
        service = WeatherService()
        result = service.get_trip_weather(prefs)

        if result.get("error"):
            return {"success": False, "forecasts": [], "error": result["error"]}

        return {"success": True, "forecasts": result.get("forecasts", [])}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    try:
        settings.validate()
        print(f"✅ Settings validated")
        print(f"📍 Primary LLM: Groq model {settings.GROQ_MODEL}")
        print(f"🌐 Starting server on http://{settings.HOST}:{settings.PORT}")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\n📝 Setup Instructions:")
        print("1. Copy backend/.env.example to backend/.env")
        print("2. Add your GROQ_API_KEY or GEMINI_KEY")
        print("3. Run the server again")
        sys.exit(1)

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )
