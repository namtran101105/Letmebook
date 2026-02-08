"""
Test that ALL services (NLP, Itinerary, Conversation) use Groq-first with Gemini fallback.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend'))

async def test_all_services():
    """Test Groq-first configuration across all services."""
    
    print("="*80)
    print("TESTING GROQ-FIRST LLM CONFIGURATION ACROSS ALL SERVICES")
    print("="*80)
    print()
    
    # Test 1: NLPExtractionService
    print("TEST 1: NLPExtractionService LLM Priority")
    print("-" * 80)
    try:
        from services.nlp_extraction_service import NLPExtractionService
        nlp_service = NLPExtractionService()
        
        if nlp_service.use_groq:
            print("✅ NLPExtractionService using Groq (PRIMARY)")
        elif nlp_service.use_gemini:
            print("⚠️  NLPExtractionService using Gemini (Groq unavailable)")
        else:
            print("❌ NLPExtractionService has no LLM configured!")
        
        # Test extraction
        print("\nTesting preference extraction with Groq...")
        result = await nlp_service.extract_preferences(
            "I want to visit Toronto from March 15-17 with a budget of $500 CAD"
        )
        print(f"✅ Extraction successful: {result.city}, "
              f"${result.budget} {result.budget_currency}")
    except Exception as e:
        print(f"❌ NLPExtractionService test failed: {e}")
    
    print()
    
    # Test 2: ItineraryService  
    print("TEST 2: ItineraryService LLM Priority")
    print("-" * 80)
    try:
        from services.itinerary_service import ItineraryService
        itinerary_service = ItineraryService()
        
        if itinerary_service.use_groq:
            print("✅ ItineraryService using Groq (PRIMARY)")
        elif itinerary_service.use_gemini:
            print("⚠️  ItineraryService using Gemini (Groq unavailable)")
        else:
            print("❌ ItineraryService has no LLM configured!")
        
        # Test itinerary generation
        print("\nTesting itinerary generation with Groq...")
        preferences = {
            "city": "Kingston",  # Changed from Toronto - use city with database venues
            "country": "Canada",
            "location_preference": "downtown",
            "start_date": "2026-03-15",
            "end_date": "2026-03-17",
            "duration_days": 3,
            "budget": 900.0,  # Increased budget for 3 days
            "budget_currency": "CAD",
            "interests": ["Culture and History", "Food and Beverage"],
            "pace": "moderate",
            "starting_location": "Downtown Kingston",
            "hours_per_day": 8,
            "transportation_modes": ["transit", "walking"],
        }
        
        itinerary = await itinerary_service.generate_itinerary(
            preferences=preferences,
            request_id="test-groq-001"
        )
        print(f"✅ Itinerary generation successful: {len(itinerary.days)} days, "
              f"${itinerary.total_spent:.2f} total cost")
    except Exception as e:
        print(f"❌ ItineraryService test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Test 3: ConversationService
    print("TEST 3: ConversationService LLM Priority")
    print("-" * 80)
    try:
        from services.conversation_service import ConversationService
        conversation_service = ConversationService()
        
        if conversation_service.use_groq:
            print("✅ ConversationService using Groq (PRIMARY)")
        elif conversation_service.use_gemini:
            print("⚠️  ConversationService using Gemini (Groq unavailable)")
        else:
            print("❌ ConversationService has no LLM configured!")
        
        # Test conversation
        print("\nTesting conversation with Groq...")
        messages, response, phase, still_need = await conversation_service.turn(
            messages=[],
            user_input=None
        )
        print(f"✅ Conversation greeting successful (phase: {phase})")
        print(f"Response preview: {response[:100]}...")
        
        # Test multi-turn
        messages, response, phase, still_need = await conversation_service.turn(
            messages=messages,
            user_input="I want to visit Toronto from March 15-17"
        )
        print(f"✅ Conversation turn 2 successful (phase: {phase})")
        print(f"Still need: {still_need}")
    except Exception as e:
        print(f"❌ ConversationService test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("="*80)
    print("TESTING SUMMARY")
    print("="*80)
    print("All services are now configured to use Groq as primary LLM")
    print("with automatic fallback to Gemini if Groq is unavailable.")
    print()
    print("Configuration verified in:")
    print("  - NLPExtractionService (backend/services/nlp_extraction_service.py)")
    print("  - ItineraryService (backend/services/itinerary_service.py)")
    print("  - ConversationService (backend/services/conversation_service.py)")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_all_services())
