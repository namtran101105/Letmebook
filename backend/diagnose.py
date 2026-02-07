#!/usr/bin/env python
"""Diagnostic script to identify setup issues."""

import sys

print("🔍 DIAGNOSTIC CHECK")
print("=" * 60)

# Check Python version
print(f"\n1. Python version: {sys.version}")

# Check required packages
print("\n2. Checking required packages...")
packages = {
    'flask': 'Flask',
    'flask_cors': 'Flask-CORS',
    'groq': 'Groq API Client',
    'dotenv': 'python-dotenv',
}

missing_packages = []
for module, name in packages.items():
    try:
        __import__(module)
        print(f"   ✅ {name} installed")
    except ImportError:
        print(f"   ❌ {name} NOT installed")
        missing_packages.append(name)

# Check .env file
print("\n3. Checking .env file...")
import os
from pathlib import Path

env_path = Path(__file__).parent / '.env'
if env_path.exists():
    print(f"   ✅ .env file exists at {env_path}")

    # Check for API key
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv('GROQ_API_KEY', '')
    if api_key:
        print(f"   ✅ GROQ_API_KEY is set (starts with '{api_key[:10]}...')")
    else:
        print(f"   ❌ GROQ_API_KEY is NOT set in .env")
else:
    print(f"   ❌ .env file NOT found at {env_path}")

# Try importing modules
print("\n4. Testing imports...")
try:
    print("   Testing config.settings...", end=" ")
    from config.settings import settings
    print("✅")
except Exception as e:
    print(f"❌ {e}")

try:
    print("   Testing models.trip_preferences...", end=" ")
    from models.trip_preferences import TripPreferences
    print("✅")
except Exception as e:
    print(f"❌ {e}")

try:
    print("   Testing clients.groq_client...", end=" ")
    from clients.groq_client import GroqClient
    print("✅")
except Exception as e:
    print(f"❌ {e}")

try:
    print("   Testing services.nlp_extraction_service...", end=" ")
    from services.nlp_extraction_service import NLPExtractionService
    print("✅")
except Exception as e:
    print(f"❌ {e}")

# Summary
print("\n" + "=" * 60)
if missing_packages:
    print("❌ SETUP INCOMPLETE")
    print("\n📦 Missing packages:")
    for pkg in missing_packages:
        print(f"   - {pkg}")
    print("\n💡 To fix, run:")
    print("   pip install -r requirements.txt")
else:
    print("✅ ALL CHECKS PASSED!")
    print("\n🚀 You can now run: python app.py")

print("=" * 60)
