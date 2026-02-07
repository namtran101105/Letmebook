"""
Flask application for Kingston Trip Planner.
Simple API for testing NLP extraction.
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from services.nlp_extraction_service import NLPExtractionService
from config.settings import settings

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

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


@app.route('/')
def index():
    """Serve the frontend HTML page."""
    return send_from_directory('../frontend', 'index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Kingston Trip Planner',
        'model': settings.GROQ_MODEL,
        'nlp_service_ready': nlp_service is not None,
        'error': nlp_service_error if nlp_service_error else None
    })


@app.route('/api/extract', methods=['POST'])
def extract_preferences():
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
        return jsonify({
            'success': False,
            'error': 'NLP service not initialized. Check your GROQ_API_KEY in .env file'
        }), 500

    try:
        # Get user input from request
        data = request.get_json()
        user_input = data.get('user_input', '').strip()

        if not user_input:
            return jsonify({
                'success': False,
                'error': 'user_input is required'
            }), 400

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

        return jsonify(response_data)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/refine', methods=['POST'])
def refine_preferences():
    """
    Refine existing preferences with additional input.

    Request body:
    {
        "preferences": {...},  # Previous preferences as dict
        "additional_input": "I'm vegetarian and want to see Fort Henry"
    }
    """
    if not nlp_service:
        return jsonify({
            'success': False,
            'error': 'NLP service not initialized'
        }), 500

    try:
        data = request.get_json()
        preferences_dict = data.get('preferences')
        additional_input = data.get('additional_input', '').strip()

        if not preferences_dict or not additional_input:
            return jsonify({
                'success': False,
                'error': 'preferences and additional_input are required'
            }), 400

        # Convert dict to TripPreferences object
        from models.trip_preferences import TripPreferences
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

        return jsonify(response_data)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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

    app.run(
        host=settings.HOST,
        port=settings.PORT,
        debug=settings.DEBUG
    )
