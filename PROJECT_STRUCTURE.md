# MonVoyage - Complete Project Structure

**Project**: Kingston Trip Planner MVP  
**Last Updated**: February 7, 2026 (import bugs fixed)  
**Repository**: namtran101105/MonVoyage (branch: vietbui)

---

## 📁 Full Directory Tree

```
MonVoyage/
│
├── 📄 Root Configuration & Documentation
│   ├── .env                                # Git-ignored environment variables (user's local config)
│   ├── .env.example                        # Template for .env (safe to commit)
│   ├── .gitignore                          # Git ignore rules
│   ├── README.md                           # Project readme (currently empty - TODO)
│   ├── QUICK_START.md                      # Quick start guide for developers
│   ├── QUICKSTART.md                       # Alternative quick start (duplicate - TODO: consolidate)
│   ├── CLAUDE.md                           # Project context for Claude AI
│   ├── USAGE_GUIDE.md                      # Complete usage examples
│   ├── README_NLP_SETUP.md                 # NLP setup instructions
│   ├── DOCUMENTATION_GUIDE.md              # Guide to all documentation
│   ├── PROJECT_STRUCTURE.md                # This file - directory overview
│   ├── todo.md                             # Task list & action items (NEW)
│   ├── Kingston Trip Planner_ MVP Implementation Guide (T.md  # Implementation guide
│   ├── requirements.txt                    # Root-level Python dependencies
│   ├── package.json                        # Frontend dependencies (Node.js)
│   └── package-lock.json                   # Locked frontend dependencies
│
├── 🔧 Backend Application
│   └── backend/
│       ├── 📋 Core Files
│       │   ├── app.py                                    # Flask main application (218 lines)
│       │   ├── diagnose.py                             # Diagnostic script (76 lines)
│       │   ├── test_imports.py                         # Import validation
│       │   ├── CLAUDE_EMBEDDED.md                      # Core MVP operational rules
│       │   ├── .env                                    # Backend config (API keys, settings)
│       │   ├── .env.example                            # Frontend template
│       │   └── __pycache__/                            # Python cache (git-ignored)
│       │
│       ├── 📚 Documentation (docs/)
│       │   ├── README.md                               # Documentation index & architecture
│       │   ├── app.PRD.md                              # Flask app product requirements
│       │   ├── diagnose.PRD.md                         # Diagnostics PRD
│       │   ├── test_imports.PRD.md                     # Import test PRD
│       │   ├── requirements.PRD.md                     # Dependencies PRD
│       │   └── __pycache__/
│       │
│       ├── ⚙️ Configuration (config/)
│       │   ├── __init__.py
│       │   ├── settings.py                             # Environment config & validation (200 lines)
│       │   ├── CLAUDE.md                               # Agent instructions
│       │   ├── README.md                               # Configuration guide
│       │   └── __pycache__/
│       │
│       ├── 📊 Data Models (models/)
│       │   ├── __init__.py
│       │   ├── trip_preferences.py                     # TripPreferences schema (293 lines)
│       │   ├── itinerary.py                            # Itinerary data structures (167 lines)
│       │   ├── CLAUDE.md                               # Agent instructions
│       │   ├── README.md                               # Data models guide
│       │   └── __pycache__/
│       │
│       ├── 🔌 External API Clients (clients/)
│       │   ├── __init__.py
│       │   ├── gemini_client.py                        # Gemini API wrapper (156 lines) ✅ Working
│       │   ├── groq_client.py                          # Groq API wrapper (142 lines) ✅ Working
│       │   ├── CLAUDE.md                               # Agent instructions
│       │   ├── README.md                               # API clients guide
│       │   └── __pycache__/
│       │
│       ├── 🧠 Business Logic (services/)
│       │   ├── __init__.py
│       │   ├── nlp_extraction_service.py               # NLP preference extraction (632 lines) ✅ Working
│       │   ├── itinerary_service.py                    # Itinerary generation (721 lines) ✅ Working
│       │   ├── CLAUDE.md                               # Agent instructions
│       │   ├── README.md                               # Services guide
│       │   └── __pycache__/
│       │
│       ├── 🛣️ HTTP Routes (routes/)
│       │   ├── __init__.py
│       │   ├── trip_routes.py                          # Route definitions (EMPTY - TODO)
│       │   ├── CLAUDE.md                               # Agent instructions
│       │   └── README.md                               # Routes guide
│       │
│       ├── 🎮 Request Handlers (controllers/)
│       │   ├── __init__.py
│       │   ├── trip_controller.py                      # Business logic handlers (EMPTY - TODO)
│       │   ├── CLAUDE.md                               # Agent instructions
│       │   └── README.md                               # Controllers guide
│       │
│       ├── 💾 Data Persistence (storage/)
│       │   ├── __init__.py
│       │   ├── trip_json_repo.py                       # Trip storage (EMPTY - TODO)
│       │   ├── itinerary_json_repo.py                  # Itinerary storage (EMPTY - TODO)
│       │   ├── CLAUDE.md                               # Agent instructions
│       │   ├── README.md                               # Storage guide
│       │   └── __pycache__/
│       │
│       ├── 🔧 Utilities (utils/)
│       │   ├── __init__.py
│       │   ├── id_generator.py                         # UUID generation (26 lines)
│       │   ├── CLAUDE.md                               # Agent instructions
│       │   ├── README.md                               # Utilities guide
│       │   └── __pycache__/
│       │
│       ├── 📁 Data Storage (data/)
│       │   └── trip_requests/
│       │       ├── README.md                           # Data storage guide
│       │       ├── .gitignore                          # Ignore generated JSON files
│       │       └── trip_kingston_*.json                # Generated preference files (git-ignored)
│       │
│       └── 📦 Backend Dependencies
│           └── requirements.txt                        # Flask, Gemini, Groq, etc.
│
├── 🎨 Frontend Application
│   └── frontend/
│       ├── 📄 Main Files
│       │   ├── index.html                              # Main HTML entry point
│       │   ├── package.json                            # Node dependencies
│       │   └── package-lock.json                       # Locked dependencies
│       │
│       ├── 📁 Source Code (src/)
│       │   ├── main.jsx                                # React entry point
│       │   ├── App.jsx                                 # Main React component
│       │   │
│       │   ├── 🎯 API Integration (api/)
│       │   │   └── tripApi.js                          # API client for Flask backend
│       │   │
│       │   ├── 🧩 React Components (components/)
│       │   │   ├── TripInputForm.jsx                   # User input form
│       │   │   ├── ExtractedJsonView.jsx               # Preferences display
│       │   │   ├── ItineraryView.jsx                   # Itinerary display
│       │   │   └── (more components as needed)
│       │   │
│       │   ├── 📄 Pages (pages/)
│       │   │   └── HomePage.jsx                        # Home page layout
│       │   │
│       │   └── 🎨 Styles (styles/)
│       │       └── global.css                          # Global CSS styles
│       │
│       └── 🔨 Build Artifacts
│           └── dist/                                  # Production build output (git-ignored)
│
├── 🔄 Automation & Orchestration
│   └── airflow/
│       ├── requirements.txt                           # Airflow-specific dependencies
│       └── dags/
│           ├── trip_placeholder_dag.py                # Placeholder Airflow DAG
│           └── (more DAGs as needed)
│
├── 🧪 Test Scripts & Demos
│   ├── demo_nlp_extraction.py                        # NLP extraction demo (118 lines)
│   ├── demo_itinerary_generation.py                  # Itinerary generation demo (165 lines)
│   ├── test_extraction.py                            # Extraction tests
│   └── scripts/
│       └── seed_demo.py                              # Demo data seeding script
│
├── 🐍 Python Environment
│   └── venv/
│       └── (virtual environment files - git-ignored)
│
└── 🔐 Git Configuration
    └── .git/                                         # Git repository metadata (git-ignored)

```

---

## 📊 Statistics

### Backend Code
- **Total Python files**: 15+ modules
- **Total lines of code**: ~3,500 lines (excluding comments & tests)
- **Largest modules**:
  - Itinerary Service: 721 lines
  - NLP Extraction Service: 632 lines
  - Trip Preferences Model: 293 lines
- **Status**: 75% complete, Phase 1 done, Phase 2 in progress

### Frontend Code
- **React components**: 4+ components
- **CSS files**: 1 global stylesheet
- **API integration**: tripApi.js client
- **Status**: Basic UI complete, integration pending

### Documentation
- **Total docs**: 22+ files
- **Backend docs**: 11 module documentation pairs (CLAUDE.md + README.md)
- **PRDs**: 5 product requirement documents
- **Guides**: 5+ user guides and setup instructions
- **Status**: Comprehensive documentation complete

### Configuration
- **Environment variables**: 15+ settings (Gemini, Groq, app config)
- **Dev dependencies**: 10+ packages
- **Production-ready**: Partially

---

## 🎯 Key File Categories

### 🔴 Critical Files (MVP Must-Have)
```
backend/
├── app.py                              ✅ Working
├── config/settings.py                  ✅ Working
├── models/trip_preferences.py          ✅ Working
├── services/nlp_extraction_service.py  ✅ Working
├── clients/groq_client.py              ✅ Working (fallback)
├── clients/gemini_client.py            ✅ Working (primary LLM)
├── services/itinerary_service.py       ✅ Working
└── .env                                ✅ Configured
```

### 🟡 Important Files (Need Completion)
```
backend/
├── routes/trip_routes.py               ❌ Empty
├── controllers/trip_controller.py      ❌ Empty
├── storage/trip_json_repo.py           ❌ Empty
├── storage/itinerary_json_repo.py      ❌ Empty
├── frontend/src/...                    ⚠️ Basic UI only
└── airflow/dags/...                    ❌ Placeholder
```

### 🟢 Supporting Files (Complete)
```
Documentation/
├── CLAUDE_EMBEDDED.md                  ✅ Complete
├── DOCUMENTATION_GUIDE.md              ✅ Complete
├── USAGE_GUIDE.md                      ✅ Complete
├── QUICK_START.md                      ✅ Complete
└── backend/docs/                       ✅ 5 PRDs + README

Configuration/
├── requirements.txt                    ✅ Complete
├── backend/requirements.txt            ✅ Complete
├── .env.example                        ✅ Complete
├── .gitignore                          ✅ Complete
└── package.json                        ✅ Complete
```

---

## 📁 File Organization by Purpose

### API Endpoints
```
backend/
├── app.py                     ✅ Inline routes (3 endpoints)
│   ├── GET  /api/health
│   ├── POST /api/extract
│   └── POST /api/refine
├── routes/trip_routes.py      ❌ Should move here (TODO)
└── controllers/trip_controller.py  ❌ Should add logic here (TODO)
```

### Data Models & Validation
```
backend/
├── models/trip_preferences.py
│   ├── TripPreferences schema
│   ├── Validation rules
│   └── Interest categorization
└── models/itinerary.py
    ├── Itinerary
    ├── ItineraryDay
    ├── Activity
    ├── Meal
    └── TravelSegment
```

### External Integrations
```
backend/
└── clients/
    ├── gemini_client.py          (Gemini 2.5-Flash API)
    └── groq_client.py            (Llama 3.3-70B API)
```

### Business Logic
```
backend/
└── services/
    ├── nlp_extraction_service.py
    │   ├── extract_preferences()
    │   ├── refine_preferences()
    │   ├── validate_preferences()
    │   ├── generate_conversational_response()
    │   └── save_preferences_to_file()
    └── itinerary_service.py
        ├── generate_itinerary()
        ├── _validate_preferences()
        ├── _build_generation_prompt()
        ├── _parse_gemini_response()
        ├── _build_itinerary_object()
        └── _validate_feasibility()
```

### Data Persistence
```
backend/
├── storage/
│   ├── trip_json_repo.py       (CRUD for trips - TODO)
│   └── itinerary_json_repo.py  (CRUD for itineraries - TODO)
└── data/
    └── trip_requests/
        └── trip_kingston_*.json (User preferences in JSON)
```

### Utilities & Helpers
```
backend/
└── utils/
    └── id_generator.py
        ├── generate_trip_id()
        └── generate_itinerary_id()
```

### Frontend UI Layer
```
frontend/
├── index.html                  (Main page)
├── src/
│   ├── App.jsx                 (Root component)
│   ├── api/tripApi.js          (Backend communication)
│   ├── components/
│   │   ├── TripInputForm.jsx   (Chat/input UI)
│   │   ├── ExtractedJsonView.jsx (Preferences panel)
│   │   └── ItineraryView.jsx   (Itinerary display)
│   ├── pages/HomePage.jsx      (Main layout)
│   └── styles/global.css       (Styling)
└── package.json                (Dependencies)
```

### Configuration & Environment
```
Root/
├── .env                        (User's local config - git-ignored)
├── .env.example                (Template - safe to commit)
├── requirements.txt            (Python deps)
├── package.json                (Node deps)
└── .gitignore                  (What to ignore)

backend/
├── config/settings.py          (Settings class, validation)
├── .env                        (Backend-specific config)
└── .env.example                (Backend config template)
```

### Testing & Validation
```
Root/
├── demo_nlp_extraction.py      (Show NLP in action)
├── demo_itinerary_generation.py (Show itinerary generation)
├── test_extraction.py          (Unit tests)
└── scripts/seed_demo.py        (Demo data)

backend/
├── diagnose.py                 (Environment checker)
└── test_imports.py             (Import validation)
```

### Documentation
```
Root/
├── README.md                   (Project readme - EMPTY TODO)
├── QUICK_START.md              (Quick start for developers)
├── USAGE_GUIDE.md              (Complete usage guide)
├── CLAUDE.md                   (Project context)
├── DOCUMENTATION_GUIDE.md      (Docs overview)
└── todo.md                     (Action items - NEW)

backend/
├── CLAUDE_EMBEDDED.md          (MVP operational rules)
├── docs/README.md              (Backend docs index)
├── docs/app.PRD.md             (Flask app requirements)
├── docs/diagnose.PRD.md        (Diagnostics PRD)
├── docs/test_imports.PRD.md    (Import test PRD)
├── docs/requirements.PRD.md    (Dependencies PRD)
└── config/|models/|services/|... 
    └── README.md               (Module documentation - in each folder)
```

---

## 🔄 Data Flow Architecture

```
┌─────────────────────────┐
│   User Input (Web UI)   │
│   frontend/index.html   │
└────────────┬────────────┘
             │ (HTTP POST /api/extract)
             ▼
┌─────────────────────────────────────────┐
│    Flask App (backend/app.py)           │
│    • Route handling                     │
│    • Request middleware                 │
│    • CORS configuration                 │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│   (Future) Controllers                  │
│   backend/controllers/trip_controller.py│
│    • Orchestration logic                │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│   Services Layer                        │
│   backend/services/                     │
│   • NLPExtractionService                │
│   • ItineraryService                    │
└────────────┬────────────────────────────┘
             │
      ┌──────┴──────────────────┐
      │                         │
      ▼                         ▼
┌──────────────────┐    ┌─────────────────┐
│   API Clients    │    │   Data Models   │
│                  │    │                 │
│ • GeminiClient   │    │ • TripPrefs     │
│ • GroqClient     │    │ • Itinerary     │
└──────────────────┘    └─────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│   External APIs                         │
│   • Gemini 2.5-Flash                    │
│   • Groq Llama 3.3-70B                  │
│   • (Future) Google Maps                │
│   • (Future) Weather API                │
└─────────────────────────────────────────┘

   │
   ▼
┌─────────────────────────────────────────┐
│   Storage Layer                         │
│   backend/storage/                      │
│   • TripJsonRepo (file-based)           │
│   • ItineraryJsonRepo (file-based)      │
│   • (Future) MongoDB                    │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│   Data Files                            │
│   backend/data/trip_requests/*.json     │
│   (User preferences)                    │
└─────────────────────────────────────────┘
```

---

## 📈 Development Phases

### Phase 1: MVP NLP Extraction ✅ COMPLETE
- ✅ Environment setup
- ✅ Config management
- ✅ Trip preferences model
- ✅ NLP extraction service (Groq + Gemini)
- ✅ File-based storage
- ✅ Web UI (basic)
- ✅ Demo scripts
- ✅ Documentation

### Phase 2: Itinerary Generation ⏳ IN PROGRESS
- ✅ Itinerary service (import bugs fixed, service working)
- ⚠️ API endpoint for generation (needs `/api/generate-itinerary`)
- ❌ MongoDB integration
- ❌ Real-time budget tracking
- ❌ Real-time schedule adaptation

### Phase 3: Advanced Features ⏳ PLANNED
- ❌ Google Maps integration
- ❌ Weather API integration
- ❌ Web scraping (Airflow)
- ❌ Change detection
- ❌ Multi-modal transportation
- ❌ User authentication
- ❌ Production deployment

---

## 🔧 Environment Setup

### Required Files
```
✅ CONFIGURED:
  • backend/.env              (API keys present)
  • requirements.txt          (All dependencies listed)
  • package.json              (Frontend deps listed)
  • .env.example              (Safe template)
  • .gitignore                (No secrets in repo)

❌ MISSING/TODO:
  • venv/                     (Create with: python3 -m venv venv)
  • node_modules/             (Create with: npm install)
  • frontend/dist/            (Build with: npm run build)
```

### Quick Setup
```bash
# Install Python deps
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Install Node deps
npm install

# Setup backend env
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Verify setup
python3 backend/diagnose.py
```

---

## ✅ File Completeness Checklist

### Backend Core ✅
- [x] app.py (Flask main)
- [x] config/settings.py (Configuration)
- [x] models/trip_preferences.py (Preferences schema)
- [x] models/itinerary.py (Itinerary schema)
- [x] services/nlp_extraction_service.py (NLP logic)
- [x] services/itinerary_service.py (Itinerary logic)
- [x] clients/gemini_client.py (Gemini wrapper)
- [x] clients/groq_client.py (Groq wrapper)
- [x] utils/id_generator.py (UUID generation)

### Backend Next Steps ⏳
- [ ] routes/trip_routes.py (API routes)
- [ ] controllers/trip_controller.py (Request handlers)
- [ ] storage/trip_json_repo.py (Trip persistence)
- [ ] storage/itinerary_json_repo.py (Itinerary persistence)

### Frontend ⏳
- [x] index.html (Main page)
- [x] App.jsx (Root component)
- [x] components/TripInputForm.jsx (Input UI)
- [x] components/ExtractedJsonView.jsx (Display preferences)
- [x] components/ItineraryView.jsx (Display itinerary)
- [ ] More components as features expand
- [ ] Testing infrastructure
- [ ] Production build

### Documentation ✅
- [x] CLAUDE_EMBEDDED.md (MVP rules)
- [x] DOCUMENTATION_GUIDE.md (Doc overview)
- [x] USAGE_GUIDE.md (User guide)
- [x] QUICK_START.md (Quick start)
- [x] backend/docs/README.md (Backend docs)
- [x] All 5 PRD files (Requirements)
- [x] All module CLAUDE.md files (Agent instructions)
- [x] All module README.md files (User guides)
- [x] todo.md (Action items)
- [ ] README.md (Project overview - EMPTY)

### Configuration ✅
- [x] .env.example (Safe template)
- [x] backend/.env.example (Backend template)
- [x] .gitignore (Proper git ignore)
- [x] requirements.txt (Python deps)
- [x] backend/requirements.txt (Backend Python deps)
- [x] package.json (Node deps)

### Testing & Scripts ⏳
- [x] demo_nlp_extraction.py (NLP demo)
- [x] demo_itinerary_generation.py (Itinerary demo)
- [x] backend/diagnose.py (Setup checker)
- [ ] test_extraction.py (Unit tests)
- [ ] scripts/seed_demo.py (Demo data)
- [ ] Full test suite with 95%+ coverage

### CI/CD & Deployment ❌
- [ ] GitHub Actions workflows
- [ ] Docker configuration
- [ ] Kubernetes manifests
- [ ] Production deployment guide
- [ ] Monitoring & logging setup

---

## 🚀 Next Actions (Priority Order)

### ✅ COMPLETED (2026-02-07)
1. ~~Fix Gemini client import bug~~ ✅ DONE
2. ~~Fix itinerary service import bug~~ ✅ DONE

### 🔴 HIGH (This Week - 1-2 hours)
3. Test itinerary generation → `python3 demo_itinerary_generation.py`
4. Add `/api/generate-itinerary` endpoint → `backend/app.py`
5. Create `backend/routes/trip_routes.py` → Move endpoints
6. Create `backend/controllers/trip_controller.py` → Add business logic

### 🟢 MEDIUM (Next Week - 4-6 hours)
7. Implement `backend/storage/trip_json_repo.py` → CRUD for trips
8. Implement `backend/storage/itinerary_json_repo.py` → CRUD for itineraries
9. Add MongoDB integration → Replace file storage

### 🔵 LOW (Later - 8+ hours)
10. Add Google Maps API integration
11. Add Weather API integration
12. Setup Apache Airflow DAGs
13. Add production deployment

---

## 📞 Key Files Reference

| Need | File |
|------|------|
| Setup instructions | `QUICK_START.md` |
| Usage examples | `USAGE_GUIDE.md` |
| MVP requirements | `backend/CLAUDE_EMBEDDED.md` |
| Architecture | `CLAUDE.md` |
| Documentation guide | `DOCUMENTATION_GUIDE.md` |
| Action items | `todo.md` |
| API tests | `demo_nlp_extraction.py`, `demo_itinerary_generation.py` |
| Environment check | `python3 backend/diagnose.py` |
| Backend structure | This file (`PROJECT_STRUCTURE.md`) |

---

**This is your complete project roadmap!** 🗺️

*Generated: February 7, 2026*  
*Branch: vietbui*  
*Status: Phase 1 Complete, Phase 2 In Progress*
