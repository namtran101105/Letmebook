# PRD: diagnose.py

**Product**: MonVoyage Kingston Trip Planner  
**Component**: System Diagnostic Utility  
**Phase**: 1 (MVP - Development Tool)  
**Last Updated**: 2026-02-07

---

## 1. Purpose

Create a diagnostic script that verifies backend environment setup and configuration:
- Checks all required environment variables
- Tests external API connectivity (Groq)
- Validates Python environment and dependencies
- Provides clear troubleshooting output
- Helps developers/agents debug setup issues

---

## 2. Scope

### In Scope (Phase 1)
- Environment variable validation (GROQ_API_KEY)
- Groq API connectivity test
- Python version check (3.8+)
- Required package verification
- Import validation for all backend modules
- File structure validation
- Configuration loading test
- Exit codes for CI/CD integration

### Out of Scope (Phase 1)
- Database connectivity (Phase 2)
- MongoDB validation (Phase 2)
- Redis connectivity (Phase 2)
- Performance benchmarks (Phase 3)
- Load testing (Phase 3)

---

## 3. Requirements

### Functional Requirements

**FR-1**: Script must check Python version
- **Acceptance Criteria**:
  - Verify Python >= 3.8
  - Display current version
  - Fail with clear message if < 3.8

**FR-2**: Script must validate environment variables
- **Acceptance Criteria**:
  - Check GROQ_API_KEY exists
  - Check GROQ_API_KEY is not empty
  - Check GROQ_API_KEY format (starts with "gsk_")
  - Redact API key in output (show first 10 chars only)

**FR-3**: Script must test Groq API connectivity
- **Acceptance Criteria**:
  - Make simple chat completion request
  - Verify 200 response
  - Measure response time
  - Handle network errors gracefully

**FR-4**: Script must verify all required packages
- **Acceptance Criteria**:
  - Check fastapi, uvicorn, pydantic, httpx, python-dotenv
  - Display installed versions
  - Warn if versions mismatch requirements.txt

**FR-5**: Script must validate backend module imports
- **Acceptance Criteria**:
  - Import all backend modules
  - Report which modules fail to import
  - Display import error tracebacks

**FR-6**: Script must check file structure
- **Acceptance Criteria**:
  - Verify all expected directories exist
  - Verify all expected Python files exist
  - List missing files/directories

**FR-7**: Script must provide actionable output
- **Acceptance Criteria**:
  - Clear ✅/❌ indicators for each check
  - Actionable error messages ("Run: pip install ...")
  - Exit code 0 if all pass, 1 if any fail

### Non-Functional Requirements

**NFR-1**: Performance
- Complete all checks in < 5 seconds
- Groq API test timeout: 10 seconds

**NFR-2**: Usability
- Colorized output (green/red) for clarity
- Progress indicators for long checks
- Summary at end (X/Y checks passed)

---

## 4. Technical Specification

### File Structure
```
backend/
├── diagnose.py              # Diagnostic script (THIS FILE)
├── requirements.txt
└── config/
    └── settings.py
```

### Implementation

**diagnose.py**:
```python
#!/usr/bin/env python3
"""
MonVoyage Backend Diagnostic Script

Verifies environment setup and external API connectivity.
Run this before starting development or debugging issues.
"""

import sys
import os
from pathlib import Path
import importlib.util

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def check_python_version():
    """Check Python version >= 3.8"""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"{GREEN}✅ Python {version.major}.{version.minor}.{version.micro}{RESET}")
        return True
    else:
        print(f"{RED}❌ Python {version.major}.{version.minor} detected. Require 3.8+{RESET}")
        print(f"{YELLOW}   Action: Install Python 3.8 or higher{RESET}")
        return False

def check_environment_variables():
    """Check required environment variables"""
    print("\n🔍 Checking environment variables...")
    
    # Load .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print(f"{YELLOW}⚠️  python-dotenv not installed, skipping .env load{RESET}")
    
    # Check GROQ_API_KEY
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print(f"{RED}❌ GROQ_API_KEY not set{RESET}")
        print(f"{YELLOW}   Action: Create .env file with GROQ_API_KEY=your_key{RESET}")
        return False
    elif not api_key.startswith("gsk_"):
        print(f"{RED}❌ GROQ_API_KEY has invalid format{RESET}")
        print(f"{YELLOW}   Action: Verify API key from Groq console{RESET}")
        return False
    else:
        redacted = api_key[:10] + "..." + api_key[-4:]
        print(f"{GREEN}✅ GROQ_API_KEY set ({redacted}){RESET}")
        return True

def check_required_packages():
    """Check required Python packages"""
    print("\n🔍 Checking required packages...")
    
    required = {
        "fastapi": "0.100.0+",
        "uvicorn": "0.23.0+",
        "pydantic": "2.0.0+",
        "httpx": "0.24.0+",
        "python-dotenv": "1.0.0+"
    }
    
    all_installed = True
    for package, min_version in required.items():
        try:
            mod = importlib.import_module(package)
            version = getattr(mod, "__version__", "unknown")
            print(f"{GREEN}✅ {package} ({version}){RESET}")
        except ImportError:
            print(f"{RED}❌ {package} not installed{RESET}")
            print(f"{YELLOW}   Action: pip install {package}{RESET}")
            all_installed = False
    
    return all_installed

def check_groq_connectivity():
    """Test Groq API connectivity"""
    print("\n🔍 Testing Groq API connectivity...")
    
    try:
        import httpx
        import os
        import time
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print(f"{YELLOW}⚠️  Skipping (no API key){RESET}")
            return False
        
        start = time.time()
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 5
                }
            )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            print(f"{GREEN}✅ Groq API responding ({elapsed:.2f}s){RESET}")
            return True
        else:
            print(f"{RED}❌ Groq API returned {response.status_code}{RESET}")
            print(f"{YELLOW}   Response: {response.text[:200]}{RESET}")
            return False
            
    except Exception as e:
        print(f"{RED}❌ Groq API test failed: {e}{RESET}")
        print(f"{YELLOW}   Action: Check network connection and API key{RESET}")
        return False

def check_backend_imports():
    """Validate backend module imports"""
    print("\n🔍 Checking backend module imports...")
    
    modules = [
        "backend.config.settings",
        "backend.models.trip_preferences",
        "backend.services.nlp_extraction_service",
        "backend.controllers.trip_controller",
        "backend.routes.trip_routes",
        "backend.clients.groq_client",
        "backend.utils.id_generator"
    ]
    
    all_imported = True
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"{GREEN}✅ {module}{RESET}")
        except Exception as e:
            print(f"{RED}❌ {module}: {str(e)[:60]}{RESET}")
            all_imported = False
    
    return all_imported

def check_file_structure():
    """Verify expected file structure"""
    print("\n🔍 Checking file structure...")
    
    expected = [
        "backend/app.py",
        "backend/requirements.txt",
        "backend/config/settings.py",
        "backend/models/trip_preferences.py",
        "backend/services/nlp_extraction_service.py",
        "backend/controllers/trip_controller.py",
        "backend/routes/trip_routes.py",
        "backend/clients/groq_client.py",
        "backend/utils/id_generator.py"
    ]
    
    all_exist = True
    for file_path in expected:
        if Path(file_path).exists():
            print(f"{GREEN}✅ {file_path}{RESET}")
        else:
            print(f"{RED}❌ {file_path} not found{RESET}")
            all_exist = False
    
    return all_exist

def main():
    """Run all diagnostic checks"""
    print("=" * 60)
    print("MonVoyage Backend Diagnostics")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Environment Variables", check_environment_variables),
        ("Required Packages", check_required_packages),
        ("Groq API Connectivity", check_groq_connectivity),
        ("Backend Imports", check_backend_imports),
        ("File Structure", check_file_structure)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            passed = check_func()
            results.append((name, passed))
        except Exception as e:
            print(f"{RED}❌ {name} check failed: {e}{RESET}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}✅{RESET}" if result else f"{RED}❌{RESET}"
        print(f"{status} {name}")
    
    print(f"\n{passed}/{total} checks passed")
    
    if passed == total:
        print(f"{GREEN}🎉 All checks passed! Backend is ready.{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}❌ Some checks failed. Fix issues above.{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## 5. Testing Requirements

### Manual Testing (Run Script)

**Test Cases**:

1. **test_all_checks_pass**
   - Setup: Complete environment
   - Run: `python backend/diagnose.py`
   - Assert: Exit code 0, all ✅

2. **test_missing_api_key**
   - Setup: Unset GROQ_API_KEY
   - Run: `python backend/diagnose.py`
   - Assert: Exit code 1, ❌ for env vars

3. **test_wrong_python_version**
   - Setup: Mock Python 3.7
   - Assert: ❌ for Python version

4. **test_missing_packages**
   - Setup: Uninstall fastapi
   - Run: Script
   - Assert: ❌ for required packages

5. **test_groq_api_down**
   - Setup: Invalid API key
   - Run: Script
   - Assert: ❌ for Groq connectivity

6. **test_missing_files**
   - Setup: Rename app.py
   - Run: Script
   - Assert: ❌ for file structure

### Automated Testing (CI/CD)

```bash
# In CI pipeline
python backend/diagnose.py
if [ $? -ne 0 ]; then
    echo "Backend diagnostics failed"
    exit 1
fi
```

---

## 6. Example Usage

### Successful Run

```bash
$ python backend/diagnose.py

============================================================
MonVoyage Backend Diagnostics
============================================================

🔍 Checking Python version...
✅ Python 3.11.5

🔍 Checking environment variables...
✅ GROQ_API_KEY set (gsk_abc123...xyz9)

🔍 Checking required packages...
✅ fastapi (0.104.1)
✅ uvicorn (0.24.0)
✅ pydantic (2.5.0)
✅ httpx (0.25.2)
✅ python-dotenv (1.0.0)

🔍 Testing Groq API connectivity...
✅ Groq API responding (0.87s)

🔍 Checking backend module imports...
✅ backend.config.settings
✅ backend.models.trip_preferences
✅ backend.services.nlp_extraction_service
...

🔍 Checking file structure...
✅ backend/app.py
✅ backend/requirements.txt
...

============================================================
Summary
============================================================
✅ Python Version
✅ Environment Variables
✅ Required Packages
✅ Groq API Connectivity
✅ Backend Imports
✅ File Structure

6/6 checks passed
🎉 All checks passed! Backend is ready.
```

---

## 7. Open Questions

1. Should we check frontend setup as well?
2. Add database connectivity check in Phase 2?
3. Include performance benchmarks (API response time targets)?

---

## 8. Future Enhancements

### Phase 2
- [ ] MongoDB connectivity check
- [ ] Redis connectivity check
- [ ] Database schema validation
- [ ] API performance benchmarks

### Phase 3
- [ ] Load testing integration
- [ ] Memory usage checks
- [ ] Disk space checks
- [ ] External service health checks (Google Maps, Weather)

---

**Maintained By**: Backend Team  
**Status**: Phase 1 - Ready for Implementation
