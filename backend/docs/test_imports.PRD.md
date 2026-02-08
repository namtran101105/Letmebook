# PRD: test_imports.py

**Product**: MonVoyage Kingston Trip Planner  
**Component**: Import Validation Test Script  
**Phase**: 1 (MVP - Development/CI Tool)  
**Last Updated**: 2026-02-07

---

## 1. Purpose

Create a simple test script that validates all backend modules can be imported:
- Catch syntax errors early
- Verify module structure is correct
- Prevent circular import issues
- Enable fast CI/CD validation
- Provide clear error messages for debugging

---

## 2. Scope

### In Scope (Phase 1)
- Import all backend modules
- Report which imports fail
- Display import error details
- Exit code for CI/CD (0 = success, 1 = fail)
- Fast execution (< 2 seconds)

### Out of Scope
- Functional testing (use pytest)
- API testing (use integration tests)
- Performance testing
- Code quality checks (use linters)

---

## 3. Requirements

### Functional Requirements

**FR-1**: Script must import all backend modules
- **Acceptance Criteria**:
  - Import config, models, services, controllers, routes, clients, utils
  - Import app.py main application
  - Import storage repositories

**FR-2**: Script must report results clearly
- **Acceptance Criteria**:
  - Print ✅ for successful imports
  - Print ❌ for failed imports
  - Display error message for failures
  - Show summary (X/Y modules imported)

**FR-3**: Script must exit with appropriate code
- **Acceptance Criteria**:
  - Exit 0 if all imports succeed
  - Exit 1 if any import fails
  - Enable CI/CD integration

**FR-4**: Script must execute quickly
- **Acceptance Criteria**:
  - Complete in < 2 seconds
  - No external API calls
  - No heavy initialization

### Non-Functional Requirements

**NFR-1**: Simplicity
- Single file, < 100 lines
- No external dependencies (beyond stdlib)
- Clear, readable output

**NFR-2**: Maintainability
- Easy to add new modules
- Self-documenting code

---

## 4. Technical Specification

### File Structure
```
backend/
├── test_imports.py          # Import validation (THIS FILE)
├── app.py
├── config/
├── models/
├── services/
├── controllers/
├── routes/
├── clients/
├── utils/
└── storage/
```

### Implementation

**test_imports.py**:
```python
#!/usr/bin/env python3
"""
Test all backend module imports.

This is a quick smoke test to catch import errors before running full tests.
Run this in CI/CD to fail fast on syntax/import issues.

Usage:
    python backend/test_imports.py
    
Exit codes:
    0 - All imports successful
    1 - One or more imports failed
"""

import sys
import importlib

# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'

# All backend modules to test
MODULES = [
    # Config
    "backend.config.settings",
    
    # Models
    "backend.models.trip_preferences",
    "backend.models.itinerary",
    
    # Services
    "backend.services.nlp_extraction_service",
    "backend.services.itinerary_service",
    
    # Controllers
    "backend.controllers.trip_controller",
    
    # Routes
    "backend.routes.trip_routes",
    
    # Clients
    "backend.clients.groq_client",
    "backend.clients.gemini_client",
    
    # Utils
    "backend.utils.id_generator",
    
    # Storage
    "backend.storage.trip_json_repo",
    "backend.storage.itinerary_json_repo",
    
    # Main app
    "backend.app",
]


def test_import(module_name: str) -> tuple[bool, str]:
    """
    Test importing a single module.
    
    Args:
        module_name: Full module path (e.g., "backend.config.settings")
    
    Returns:
        (success, error_message)
    """
    try:
        importlib.import_module(module_name)
        return (True, "")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        return (False, error_msg)


def main():
    """Run import tests for all modules"""
    print("Testing backend module imports...")
    print("=" * 60)
    
    results = []
    
    for module in MODULES:
        success, error = test_import(module)
        results.append((module, success, error))
        
        if success:
            print(f"{GREEN}✅{RESET} {module}")
        else:
            print(f"{RED}❌{RESET} {module}")
            print(f"   {RED}{error}{RESET}")
    
    # Summary
    print("=" * 60)
    successful = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"\n{successful}/{total} modules imported successfully")
    
    if successful == total:
        print(f"{GREEN}✅ All imports passed!{RESET}")
        sys.exit(0)
    else:
        failed = [module for module, success, _ in results if not success]
        print(f"{RED}❌ Failed imports:{RESET}")
        for module in failed:
            print(f"   - {module}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## 5. Testing Requirements

### Manual Testing

**Test Cases**:

1. **test_all_imports_succeed**
   - Setup: Complete backend implementation
   - Run: `python backend/test_imports.py`
   - Assert: Exit code 0, all modules ✅

2. **test_syntax_error**
   - Setup: Add syntax error to settings.py
   - Run: Script
   - Assert: Exit code 1, ❌ for settings module

3. **test_missing_dependency**
   - Setup: Uninstall fastapi
   - Run: Script
   - Assert: Exit code 1, shows import error

4. **test_circular_import**
   - Setup: Create circular import
   - Run: Script
   - Assert: Exit code 1, shows circular import error

5. **test_execution_speed**
   - Run: `time python backend/test_imports.py`
   - Assert: Completes in < 2 seconds

### CI/CD Integration

```yaml
# In .github/workflows/test.yml
- name: Test imports
  run: python backend/test_imports.py
  
- name: Run full tests
  run: pytest backend/tests/
```

---

## 6. Example Usage

### Successful Run

```bash
$ python backend/test_imports.py

Testing backend module imports...
============================================================
✅ backend.config.settings
✅ backend.models.trip_preferences
✅ backend.models.itinerary
✅ backend.services.nlp_extraction_service
✅ backend.services.itinerary_service
✅ backend.controllers.trip_controller
✅ backend.routes.trip_routes
✅ backend.clients.groq_client
✅ backend.clients.gemini_client
✅ backend.utils.id_generator
✅ backend.storage.trip_json_repo
✅ backend.storage.itinerary_json_repo
✅ backend.app
============================================================

13/13 modules imported successfully
✅ All imports passed!

$ echo $?
0
```

### Failed Run (Syntax Error)

```bash
$ python backend/test_imports.py

Testing backend module imports...
============================================================
✅ backend.config.settings
❌ backend.models.trip_preferences
   SyntaxError: invalid syntax (trip_preferences.py, line 42)
✅ backend.models.itinerary
...
============================================================

12/13 modules imported successfully
❌ Failed imports:
   - backend.models.trip_preferences

$ echo $?
1
```

---

## 7. Integration with CI/CD

### GitHub Actions

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r backend/requirements.txt
      
      - name: Test imports (fast fail)
        run: python backend/test_imports.py
      
      - name: Run full test suite
        run: pytest backend/tests/
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Testing backend imports..."
python backend/test_imports.py

if [ $? -ne 0 ]; then
    echo "Import tests failed. Fix errors before committing."
    exit 1
fi
```

---

## 8. Comparison with Other Tools

### vs pytest
- **test_imports.py**: Fast (< 2s), syntax/import errors only
- **pytest**: Slow (10s+), functional tests, requires fixtures

**Use both**: Run test_imports.py first for fast fail, then pytest for full validation

### vs pylint/flake8
- **test_imports.py**: Runtime import validation
- **linters**: Static analysis, code quality

**Use both**: Linters catch style issues, test_imports catches runtime errors

---

## 9. Open Questions

1. Should we include frontend imports as well?
2. Add import time measurement for performance tracking?
3. Integrate with code coverage tools?

---

## 10. Future Enhancements

### Phase 2
- [ ] Measure import time for each module
- [ ] Detect circular imports explicitly
- [ ] Validate __all__ exports

### Phase 3
- [ ] Frontend import validation
- [ ] Import graph visualization
- [ ] Performance regression tracking

---

## 11. Acceptance Criteria Summary

✅ **DONE**: Imports all backend modules  
✅ **DONE**: Reports success/failure clearly  
✅ **DONE**: Exits with appropriate code  
✅ **DONE**: Executes in < 2 seconds  
✅ **DONE**: Works in CI/CD pipelines  
✅ **DONE**: Clear error messages

---

**Maintained By**: Backend Team  
**Status**: Phase 1 - Ready for Implementation
