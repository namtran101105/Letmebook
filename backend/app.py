"""
MonVoyage Trip Planner — FastAPI application.

Orchestrates NLP extraction, itinerary generation, and venue data from
the Airflow-managed database.  Serves the frontend at ``/`` and exposes
a REST API under ``/api/*``.

Run:
    python backend/app.py          # starts uvicorn with reload
    uvicorn app:app --reload       # (from the backend/ directory)

Auto-generated API docs:
    http://localhost:8000/docs      (Swagger UI)
    http://localhost:8000/redoc     (ReDoc)
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup — allow short imports like ``from config.settings import …``
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from config.settings import settings
from services.nlp_extraction_service import NLPExtractionService
from services.itinerary_service import ItineraryService, ItineraryGenerationError
from clients.gemini_client import ExternalAPIError
from models.trip_preferences import TripPreferences
from utils.id_generator import generate_trip_id
from schemas.api_models import (
    ExtractRequest,
    ExtractResponse,
    RefineRequest,
    RefineResponse,
    GenerateItineraryRequest,
    GenerateItineraryResponse,
    HealthResponse,
    ValidationResult,
    FeasibilityResult,
    ChatRequest,
    ChatResponse,
    ChatMessage,
)
from services.conversation_service import ConversationService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level service instances (set during lifespan startup)
# ---------------------------------------------------------------------------
nlp_service: Optional[NLPExtractionService] = None
itinerary_service: Optional[ItineraryService] = None
conversation_service: Optional[ConversationService] = None
nlp_service_error: Optional[str] = None


# ---------------------------------------------------------------------------
# Lifespan — initialise / tear down services
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialise services on startup; clean up on shutdown."""
    global nlp_service, itinerary_service, conversation_service, nlp_service_error

    try:
        nlp_service = NLPExtractionService()
        print("✅ NLP Extraction Service initialized successfully")
    except Exception as exc:
        nlp_service_error = str(exc)
        print(f"❌ Failed to initialize NLP service: {exc}")
        import traceback
        traceback.print_exc()

    try:
        itinerary_service = ItineraryService()
        print("✅ Itinerary Service initialized successfully")
    except Exception as exc:
        print(f"⚠️  Itinerary Service init failed (will still serve NLP): {exc}")

    try:
        conversation_service = ConversationService()
        print("✅ Conversation Service initialized successfully")
    except Exception as exc:
        print(f"⚠️  Conversation Service init failed: {exc}")

    yield  # ── application runs here ──

    logger.info("Shutting down MonVoyage")


# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MonVoyage Trip Planner",
    version="0.2.0",
    description="AI-powered itinerary engine for any city worldwide.",
    lifespan=lifespan,
)

# CORS — allow all origins (matches previous Flask-CORS default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(ItineraryGenerationError)
async def _itinerary_error(request: Request, exc: ItineraryGenerationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": exc.reason,
            "constraints": exc.constraints,
        },
    )


@app.exception_handler(ExternalAPIError)
async def _external_api_error(request: Request, exc: ExternalAPIError):
    return JSONResponse(
        status_code=502,
        content={
            "success": False,
            "error": f"{exc.service} API failed: {exc.error}",
        },
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# ── Frontend ────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def index():
    """Serve the frontend HTML page."""
    frontend_path = os.path.join(
        os.path.dirname(__file__), "..", "frontend", "index.html",
    )
    return FileResponse(frontend_path)


# ── Health check ────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Return service health and active LLM information."""
    if nlp_service:
        if nlp_service.use_gemini:
            model_info = f"Gemini ({settings.GEMINI_MODEL})"
            primary = "gemini"
        else:
            model_info = f"Groq ({settings.GROQ_MODEL})"
            primary = "groq"
    else:
        model_info = "Not initialized"
        primary = "none"

    return HealthResponse(
        status="healthy",
        service="MonVoyage Trip Planner",
        primary_llm=primary,
        model=model_info,
        nlp_service_ready=nlp_service is not None,
        error=nlp_service_error,
    )


# ── Extract preferences ────────────────────────────────────────

@app.post("/api/extract", response_model=ExtractResponse, tags=["preferences"])
async def extract_preferences(body: ExtractRequest):
    """
    Extract structured trip preferences from a natural-language message.

    The NLP service parses the user's input and returns a structured
    ``TripPreferences`` dict together with validation results and a
    conversational bot reply.
    """
    if not nlp_service:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "NLP service not initialized. Check your API keys in .env file",
            },
        )

    try:
        # Extract → validate → generate conversational response
        preferences = await nlp_service.extract_preferences(body.user_input)
        validation = nlp_service.validate_preferences(preferences)
        bot_message, all_questions_asked = await nlp_service.generate_conversational_response(
            user_input=body.user_input,
            preferences=preferences,
            validation=validation,
            is_refinement=False,
        )

        # Persist to file when all required questions have been answered
        saved_file_path = None
        if all_questions_asked:
            saved_file_path = nlp_service.save_preferences_to_file(preferences)

        return ExtractResponse(
            success=True,
            preferences=preferences.to_dict(),
            validation=ValidationResult(**validation),
            bot_message=bot_message,
            saved_to_file=saved_file_path,
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(exc)},
        )


# ── Refine preferences ─────────────────────────────────────────

@app.post("/api/refine", response_model=RefineResponse, tags=["preferences"])
async def refine_preferences(body: RefineRequest):
    """
    Refine previously extracted preferences with follow-up user input.

    Accepts the prior ``preferences`` dict and an ``additional_input``
    string, merges the new information, and returns the updated result.
    """
    if not nlp_service:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "NLP service not initialized"},
        )

    try:
        existing = TripPreferences.from_dict(body.preferences)
        refined = await nlp_service.refine_preferences(existing, body.additional_input)
        validation = nlp_service.validate_preferences(refined)
        bot_message, all_questions_asked = await nlp_service.generate_conversational_response(
            user_input=body.additional_input,
            preferences=refined,
            validation=validation,
            is_refinement=True,
        )

        saved_file_path = None
        if all_questions_asked:
            saved_file_path = nlp_service.save_preferences_to_file(refined)

        return RefineResponse(
            success=True,
            preferences=refined.to_dict(),
            validation=ValidationResult(**validation),
            bot_message=bot_message,
            saved_to_file=saved_file_path,
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(exc)},
        )


# ── Generate itinerary ─────────────────────────────────────────

@app.post(
    "/api/generate-itinerary",
    response_model=GenerateItineraryResponse,
    tags=["itinerary"],
)
async def generate_itinerary_endpoint(body: GenerateItineraryRequest):
    """
    Generate a day-by-day itinerary from complete trip preferences.

    Requires all 10 mandatory preference fields.  The service queries
    the Airflow venue database for real venue data (when available) and
    calls the Gemini API to produce a feasible timetable.
    """
    if not itinerary_service:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": "Itinerary service not initialized",
            },
        )

    try:
        request_id = generate_trip_id()
        itinerary = await itinerary_service.generate_itinerary(
            preferences=body.preferences,
            request_id=request_id,
        )

        # Re-run feasibility for the response envelope (cheap, no I/O)
        feasibility = itinerary_service._validate_feasibility(
            itinerary, body.preferences, request_id,
        )

        return GenerateItineraryResponse(
            success=True,
            itinerary=itinerary.to_dict(),
            feasibility=FeasibilityResult(**feasibility),
        )

    except ValueError as exc:
        # Validation errors (missing fields, budget too low, etc.)
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(exc)},
        )
    except ItineraryGenerationError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": exc.reason,
                "feasibility": exc.constraints,
            },
        )
    except Exception as exc:
        logger.error("Itinerary generation failed", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(exc)},
        )


# ── Conversational chat (Toronto MVP) ─────────────────────────

@app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
async def chat(body: ChatRequest):
    """
    Conversational Toronto trip-planning assistant.

    Send an empty ``messages`` list to receive the greeting.  On subsequent
    turns, include the full ``messages`` array from the previous response
    together with the new ``user_input``.

    The service progresses through phases:
    ``greeting`` → ``intake`` → ``confirmed`` → ``itinerary``.
    """
    if not conversation_service:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": "Conversation service not initialized. Check GROQ_API_KEY in .env",
            },
        )

    try:
        messages_raw = [m.model_dump() for m in body.messages]

        updated_messages, assistant_text, phase, still_need = (
            await conversation_service.turn(
                messages=messages_raw,
                user_input=body.user_input,
            )
        )

        return ChatResponse(
            success=True,
            messages=[ChatMessage(**m) for m in updated_messages],
            assistant_message=assistant_text,
            phase=phase,
            still_need=still_need,
        )

    except Exception as exc:
        logger.error("Chat turn failed", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(exc)},
        )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    errors = settings.validate()
    if errors:
        for err in errors:
            print(f"❌ Configuration error: {err}")
        print("\n📝 Setup Instructions:")
        print("1. Copy backend/.env.example to backend/.env")
        print("2. Add your Gemini API key from https://aistudio.google.com/apikey")
        print("3. (Optional) Add your Groq API key from https://console.groq.com/keys")
        print("4. Run the server again")
        sys.exit(1)

    print(f"✅ Settings validated")
    print(f"🌐 Starting server on http://{settings.HOST}:{settings.PORT}")
    print(f"📖 API docs at http://{settings.HOST}:{settings.PORT}/docs")

    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
