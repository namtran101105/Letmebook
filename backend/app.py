"""
FastAPI application for Kingston Trip Planner.
Simple API for testing NLP extraction.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys
import os
import uvicorn

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from services.nlp_extraction_service import NLPExtractionService
from models.trip_preferences import TripPreferences
from config.settings import settings

# Initialize FastAPI app
app = FastAPI(
    title="Kingston Trip Planner",
    description="API for travel planning with NLP extraction",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Initialize service
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


# Pydantic models for request/response validation
class ExtractRequest(BaseModel):
    user_input: str


class RefineRequest(BaseModel):
    preferences: Dict[str, Any]
    additional_input: str


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
        'service': 'Kingston Trip Planner',
        'model': settings.GROQ_MODEL,
        'nlp_service_ready': nlp_service is not None,
        'error': nlp_service_error if nlp_service_error else None
    }


@app.post('/api/extract', response_model=TripResponse)
async def extract_preferences(request: ExtractRequest):
    """
    Extract trip preferences from user input.

    Request body:
    {
        "user_input": "I want to visit Kingston next weekend with my family..."
    }

    Response:
    {
        "success": true,
        "trip_id": "trip_123...",
        "preferences": {...},
        "validation": {...}
    }
    """
    if not nlp_service:
        raise HTTPException(
            status_code=500,
            detail='NLP service not initialized. Check your GROQ_API_KEY in .env file'
        )

    try:
        user_input = request.user_input.strip()

        if not user_input:
            raise HTTPException(status_code=400, detail='user_input is required')

        # Extract preferences
        preferences = nlp_service.extract_preferences(user_input)

        # Validate preferences
        validation = nlp_service.validate_preferences(preferences)

        # Generate conversational response
        bot_message, all_questions_asked = nlp_service.generate_conversational_response(
            user_input=user_input,
            preferences=preferences,
            validation=validation,
            is_refinement=False
        )

        # If all questions have been asked, save to JSON file
        saved_file_path = None
        if all_questions_asked:
            saved_file_path = nlp_service.save_preferences_to_file(preferences)

        # Return results
        response_data = {
            'success': True,
            'preferences': preferences.to_dict(),
            'validation': validation,
            'bot_message': bot_message
        }

        # Include file path if saved
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
    Refine existing preferences with additional input.

    Request body:
    {
        "preferences": {...},  # Previous preferences as dict
        "additional_input": "I'm vegetarian and want to see Fort Henry"
    }
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

        # Refine preferences
        refined = nlp_service.refine_preferences(existing_preferences, additional_input)

        # Validate
        validation = nlp_service.validate_preferences(refined)

        # Generate conversational response for refinement
        bot_message, all_questions_asked = nlp_service.generate_conversational_response(
            user_input=additional_input,
            preferences=refined,
            validation=validation,
            is_refinement=True
        )

        # If all questions have been asked, save to JSON file
        saved_file_path = None
        if all_questions_asked:
            saved_file_path = nlp_service.save_preferences_to_file(refined)

        # Return results
        response_data = {
            'success': True,
            'preferences': refined.to_dict(),
            'validation': validation,
            'bot_message': bot_message
        }

        # Include file path if saved
        if saved_file_path:
            response_data['saved_to_file'] = saved_file_path

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    # Validate settings
    try:
        settings.validate()
        print(f"✅ Settings validated")
        print(f"📍 Using Groq model: {settings.GROQ_MODEL}")
        print(f"🌐 Starting server on http://{settings.HOST}:{settings.PORT}")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\n📝 Setup Instructions:")
        print("1. Copy backend/.env.example to backend/.env")
        print("2. Add your Groq API key from https://console.groq.com/keys")
        print("3. Run the server again")
        sys.exit(1)

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )
