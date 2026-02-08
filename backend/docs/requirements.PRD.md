# PRD: requirements.txt

**Product**: MonVoyage Kingston Trip Planner  
**Component**: Python Dependencies Specification  
**Phase**: 1 (MVP)  
**Last Updated**: 2026-02-07

---

## 1. Purpose

Define all Python package dependencies for the MonVoyage backend:
- Specify exact or minimum versions
- Document purpose of each dependency
- Enable reproducible builds
- Support development and production environments

---

## 2. Scope

### In Scope (Phase 1)
- Web framework (FastAPI)
- ASGI server (Uvicorn)
- Data validation (Pydantic)
- HTTP client (httpx)
- Environment variables (python-dotenv)
- Testing framework (pytest)
- Code quality tools (basic)

### Out of Scope (Phase 1)
- Database drivers (Phase 2: pymongo)
- Caching (Phase 2: redis)
- Task queue (Phase 3: celery)
- Monitoring (Phase 3: sentry-sdk)

---

## 3. Requirements

### Functional Requirements

**FR-1**: requirements.txt must include all runtime dependencies
- **Acceptance Criteria**:
  - FastAPI for web framework
  - Uvicorn for ASGI server
  - Pydantic for data validation
  - httpx for async HTTP client
  - python-dotenv for environment variables

**FR-2**: requirements.txt must include development dependencies
- **Acceptance Criteria**:
  - pytest for testing
  - pytest-asyncio for async tests
  - pytest-cov for coverage
  - httpx for test client

**FR-3**: requirements.txt must specify version constraints
- **Acceptance Criteria**:
  - Pin major versions (fastapi>=0.100,<1.0)
  - Allow minor/patch updates
  - Document breaking version changes

**FR-4**: requirements.txt must be organized and commented
- **Acceptance Criteria**:
  - Group by purpose (web, testing, utils)
  - Comment each dependency's purpose
  - Alphabetize within groups

### Non-Functional Requirements

**NFR-1**: Compatibility
- Support Python 3.8+
- No conflicting dependencies
- Compatible versions across all packages

**NFR-2**: Security
- Use latest stable versions
- No known vulnerabilities
- Regular updates

---

## 4. Technical Specification

### File Structure
```
backend/
├── requirements.txt         # Production dependencies (THIS FILE)
└── requirements-dev.txt     # Optional: Development-only dependencies
```

### Implementation

**requirements.txt**:
```txt
# ============================================================
# MonVoyage Backend Dependencies
# Phase 1 (MVP) - NLP Extraction & Itinerary Generation
# ============================================================

# Web Framework
fastapi>=0.104.0,<1.0.0      # Modern async web framework
uvicorn[standard]>=0.24.0    # ASGI server with websockets support
pydantic>=2.5.0,<3.0.0       # Data validation and settings management

# HTTP Client
httpx>=0.25.0                # Async HTTP client for external APIs

# Environment & Configuration
python-dotenv>=1.0.0         # Load environment variables from .env

# Testing
pytest>=7.4.0                # Testing framework
pytest-asyncio>=0.21.0       # Async test support
pytest-cov>=4.1.0            # Code coverage reporting

# Code Quality (Optional)
# black>=23.0.0              # Code formatter
# ruff>=0.1.0                # Fast Python linter
# mypy>=1.7.0                # Static type checker

# ============================================================
# Phase 2 (Planned) - Database & Caching
# ============================================================
# pymongo>=4.6.0             # MongoDB driver
# redis>=5.0.0               # Redis client for caching
# motor>=3.3.0               # Async MongoDB driver

# ============================================================
# Phase 3 (Planned) - Task Queue & Monitoring
# ============================================================
# celery>=5.3.0              # Distributed task queue
# sentry-sdk[fastapi]>=1.38  # Error tracking and monitoring
```

**Optional requirements-dev.txt** (development only):
```txt
# Development dependencies (not needed in production)

# Code Quality
black>=23.0.0                # Code formatter
ruff>=0.1.0                  # Fast linter
mypy>=1.7.0                  # Type checker

# Documentation
mkdocs>=1.5.0                # Documentation generator
mkdocs-material>=9.0.0       # Material theme for docs

# Debugging
ipython>=8.17.0              # Enhanced Python shell
ipdb>=0.13.0                 # IPython-based debugger
```

---

## 5. Dependency Details

### FastAPI (>=0.104.0)
**Purpose**: Web framework for API endpoints  
**Why this version**: 0.104+ has improved async support  
**Breaking changes**: v1.0 may change API, hence <1.0.0

### Uvicorn (>=0.24.0)
**Purpose**: ASGI server to run FastAPI  
**Why this version**: 0.24+ has better WebSocket support  
**Note**: `[standard]` includes extra dependencies (websockets, httptools)

### Pydantic (>=2.5.0, <3.0.0)
**Purpose**: Data validation, settings, request/response models  
**Why this version**: v2 has major performance improvements  
**Breaking changes**: v3 will break API, hence <3.0.0

### httpx (>=0.25.0)
**Purpose**: Async HTTP client for Groq API  
**Why not requests**: requests is synchronous, httpx supports async/await

### python-dotenv (>=1.0.0)
**Purpose**: Load GROQ_API_KEY from .env file  
**Why this version**: 1.0+ is stable release

### pytest (>=7.4.0)
**Purpose**: Testing framework  
**Why this version**: 7.4+ supports Python 3.12

### pytest-asyncio (>=0.21.0)
**Purpose**: Run async tests with pytest  
**Required for**: Testing async controllers and services

### pytest-cov (>=4.1.0)
**Purpose**: Generate code coverage reports  
**Target**: 95%+ test coverage

---

## 6. Installation Instructions

### Initial Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Optional: Install dev dependencies
pip install -r backend/requirements-dev.txt

# Verify installation
pip list
```

### Updating Dependencies

```bash
# Update all packages to latest compatible versions
pip install --upgrade -r backend/requirements.txt

# Update specific package
pip install --upgrade fastapi

# Regenerate requirements (after manual changes)
pip freeze > backend/requirements.txt
```

---

## 7. Testing Requirements

### Validation Tests

**Test Cases**:

1. **test_all_packages_install**
   ```bash
   pip install -r requirements.txt
   # Assert: No errors, all packages installed
   ```

2. **test_no_version_conflicts**
   ```bash
   pip check
   # Assert: No dependency conflicts
   ```

3. **test_import_all_packages**
   ```bash
   python -c "import fastapi, uvicorn, pydantic, httpx, dotenv, pytest"
   # Assert: All imports successful
   ```

4. **test_python_version_compatibility**
   - Test on Python 3.8, 3.9, 3.10, 3.11
   - Assert: All versions install successfully

5. **test_security_vulnerabilities**
   ```bash
   pip install safety
   safety check
   # Assert: No known vulnerabilities
   ```

---

## 8. Version Upgrade Strategy

### When to Upgrade

**Minor/Patch Versions**: Upgrade quarterly
- Security patches
- Bug fixes
- New minor features

**Major Versions**: Upgrade carefully
- Test thoroughly
- Check breaking changes
- Update code if needed

### Upgrade Process

1. **Check changelog** for breaking changes
2. **Update requirements.txt** with new version
3. **Install in dev environment**
   ```bash
   pip install --upgrade package_name
   ```
4. **Run all tests**
   ```bash
   pytest backend/tests/
   ```
5. **Test application manually**
6. **Update requirements.txt**
   ```bash
   pip freeze | grep package_name >> requirements.txt
   ```
7. **Commit changes**

---

## 9. Known Issues

### Issue: Pydantic v2 Breaking Changes

**Problem**: Pydantic v1 → v2 has breaking API changes

**Solution**: Pin to v2.x and < v3.0.0
```txt
pydantic>=2.5.0,<3.0.0
```

### Issue: FastAPI v1.0 Not Released

**Problem**: FastAPI hasn't released v1.0 yet

**Solution**: Pin to >= 0.104.0, < 1.0.0 to avoid breaking changes
```txt
fastapi>=0.104.0,<1.0.0
```

---

## 10. Phase 2/3 Dependencies

### Phase 2 (Database & Caching)

```txt
# Database
pymongo>=4.6.0               # MongoDB driver
motor>=3.3.0                 # Async MongoDB driver

# Caching
redis>=5.0.0                 # Redis client

# Migrations
alembic>=1.13.0              # Database migrations (if using SQL later)
```

### Phase 3 (Task Queue & Monitoring)

```txt
# Task Queue
celery>=5.3.0                # Distributed task queue
redis>=5.0.0                 # Celery backend

# Monitoring
sentry-sdk[fastapi]>=1.38.0  # Error tracking
prometheus-client>=0.19.0    # Metrics

# Rate Limiting
slowapi>=0.1.9               # Rate limiting for FastAPI
```

---

## 11. Example: Full requirements.txt

```txt
# ============================================================
# MonVoyage Backend - Production Dependencies
# ============================================================

# Core Web Framework
fastapi>=0.104.0,<1.0.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0,<3.0.0

# HTTP & External APIs
httpx>=0.25.0

# Configuration
python-dotenv>=1.0.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0

# ============================================================
# Installation:
#   pip install -r requirements.txt
#
# Upgrade:
#   pip install --upgrade -r requirements.txt
#
# Verify:
#   pip check
#   python backend/test_imports.py
# ============================================================
```

---

## 12. Acceptance Criteria Summary

✅ **DONE**: All runtime dependencies listed  
✅ **DONE**: Version constraints specified  
✅ **DONE**: Organized with comments  
✅ **DONE**: Compatible with Python 3.8+  
✅ **DONE**: No version conflicts  
✅ **DONE**: Installation instructions provided  
✅ **DONE**: Upgrade strategy documented  
✅ **DONE**: Security considerations noted

---

**Maintained By**: Backend Team  
**Reviewed By**: Technical Lead  
**Status**: Phase 1 - Ready for Implementation
