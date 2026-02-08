#!/usr/bin/env python3
"""
Demo script for NLP Extraction Service.
Shows how to extract trip preferences from natural language input.
"""
import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend'))

from services.nlp_extraction_service import NLPExtractionService


def main():
    print("=" * 70)
    print("  NLP EXTRACTION SERVICE - DEMO")
    print("=" * 70)

    # Initialize service (uses Gemini by default, falls back to Groq)
    print("\n[1] Initializing NLP Extraction Service...")
    service = NLPExtractionService(use_gemini=True)

    # Example 1: Basic trip planning
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Trip")
    print("=" * 70)

    user_input_1 = """
    I want to visit Kingston from May 10-12, 2026.
    My budget is $900 total. I love museums, food tours, and waterfront activities.
    I prefer a moderate pace and want to stay downtown.
    """

    print(f"\nUser Input:\n{user_input_1}")
    print("\n[Extracting preferences...]")

    preferences_1 = service.extract_preferences(user_input_1)
    validation_1 = service.validate_preferences(preferences_1)

    print(f"\n✅ Extraction Complete!")
    print(f"   Completeness: {validation_1['completeness_score'] * 100:.0f}%")
    print(f"   Valid: {validation_1['valid']}")

    print(f"\nExtracted Preferences:")
    print(json.dumps(preferences_1.to_dict(), indent=2))

    # Example 2: Incomplete information (needs refinement)
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Incomplete Trip (Needs Refinement)")
    print("=" * 70)

    user_input_2 = "I want to visit Kingston next weekend with $400 budget"

    print(f"\nUser Input:\n{user_input_2}")
    print("\n[Extracting preferences...]")

    preferences_2 = service.extract_preferences(user_input_2)
    validation_2 = service.validate_preferences(preferences_2)

    print(f"\n⚠️  Incomplete Extraction")
    print(f"   Completeness: {validation_2['completeness_score'] * 100:.0f}%")
    print(f"   Valid: {validation_2['valid']}")
    print(f"   Missing: {validation_2['issues']}")

    print(f"\nExtracted Preferences:")
    print(json.dumps(preferences_2.to_dict(), indent=2))

    # Refine with additional information
    print("\n[Refining with additional details...]")
    additional_input = "I'm interested in history and food. Prefer relaxed pace, downtown location."

    refined_preferences = service.refine_preferences(preferences_2, additional_input)
    refined_validation = service.validate_preferences(refined_preferences)

    print(f"\n✅ Refinement Complete!")
    print(f"   Completeness: {refined_validation['completeness_score'] * 100:.0f}%")
    print(f"   Valid: {refined_validation['valid']}")

    print(f"\nRefined Preferences:")
    print(json.dumps(refined_preferences.to_dict(), indent=2))

    # Example 3: Generate conversational response
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Conversational Response")
    print("=" * 70)

    bot_message, all_complete = service.generate_conversational_response(
        user_input=user_input_1,
        preferences=preferences_1,
        validation=validation_1,
        is_refinement=False
    )

    print(f"\nBot Response:\n{bot_message}")
    print(f"\nAll questions asked: {all_complete}")

    print("\n" + "=" * 70)
    print("  DEMO COMPLETE!")
    print("=" * 70)
    print("\n💡 Tips:")
    print("  - The service uses Gemini API by default")
    print("  - Falls back to Groq if Gemini is unavailable")
    print("  - Preferences are auto-saved when complete")
    print("  - Check backend/data/ for saved preferences")


if __name__ == "__main__":
    main()
