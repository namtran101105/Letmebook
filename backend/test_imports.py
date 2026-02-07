#!/usr/bin/env python
"""Quick test to verify all imports work correctly."""

print("Testing imports...")

try:
    print("1. Importing settings...", end=" ")
    from config.settings import settings
    print("✅")

    print("2. Importing TripPreferences...", end=" ")
    from models.trip_preferences import TripPreferences
    print("✅")

    print("3. Importing id_generator...", end=" ")
    from utils.id_generator import generate_trip_id
    print("✅")

    print("4. Importing GroqClient...", end=" ")
    from clients.groq_client import GroqClient
    print("✅")

    print("5. Importing NLPExtractionService...", end=" ")
    from services.nlp_extraction_service import NLPExtractionService
    print("✅")

    print("\n" + "="*50)
    print("All imports successful! ✅")
    print("="*50)

    print(f"\nAPI Key configured: {'Yes ✅' if settings.GROQ_API_KEY else 'No ❌'}")
    print(f"Model: {settings.GROQ_MODEL}")
    print(f"Port: {settings.PORT}")

    print("\n🚀 Ready to run: python app.py")

except ImportError as e:
    print(f"\n❌ Import Error: {e}")
    print("\nMake sure you:")
    print("1. Activated your venv")
    print("2. Installed dependencies: pip install -r requirements.txt")
except Exception as e:
    print(f"\n❌ Error: {e}")
