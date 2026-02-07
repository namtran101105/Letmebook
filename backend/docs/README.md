# MonVoyage Backend Documentation Index

**Project**: Kingston Trip Planner MVP  
**Phase**: 1 (NLP Extraction & Itinerary Generation)  
**Last Updated**: 2026-02-07

---

## Overview

This directory contains comprehensive documentation for the MonVoyage backend. Documentation is organized in two formats:

1. **CLAUDE.md** files - Agent-oriented instructions for AI code generation
2. **README.md** files - Human-oriented module documentation
3. **PRD.md** files - Product Requirements Documents for key files

---

## Quick Links

### Essential Reading

- [Backend Operational Rules](../CLAUDE_EMBEDDED.md) - **START HERE** - MVP requirements, logging standards, testing requirements
- [Documentation Status](../DOCUMENTATION_STATUS.md) - Current progress and next steps

### For Humans (README.md)

- [Config Module](../config/README.md) - Environment variables, settings management
- [Models Module](../models/README.md) - Data structures, validation
- [Services Module](../services/README.md) - Business logic, NLP extraction
- [Controllers Module](../controllers/README.md) - Request orchestration
- [Routes Module](../routes/README.md) - HTTP endpoints, API documentation
- [Clients Module](../clients/README.md) - External API wrappers (Groq)
- [Utils Module](../utils/README.md) - ID generation, date handling
- [Storage Module](../storage/README.md) - Data persistence (JSON/MongoDB)

### For AI Agents (CLAUDE.md)

- [Config Instructions](../config/CLAUDE.md)
- [Models Instructions](../models/CLAUDE.md)
- [Services Instructions](../services/CLAUDE.md)
- [Controllers Instructions](../controllers/CLAUDE.md)
- [Routes Instructions](../routes/CLAUDE.md)
- [Clients Instructions](../clients/CLAUDE.md)
- [Utils Instructions](../utils/CLAUDE.md)
- [Storage Instructions](../storage/CLAUDE.md)

### Product Requirements (PRD)

- [app.py PRD](app.PRD.md) - Main FastAPI application specification
- [diagnose.py PRD](diagnose.PRD.md) - System diagnostics utility
- [test_imports.py PRD](test_imports.PRD.md) - Import validation script
- [requirements.txt PRD](requirements.PRD.md) - Dependency management

---

## Documentation Structure

### Module Documentation Pattern

Each backend module has two documentation files:

```
backend/<module>/
├── CLAUDE.md          # For AI agents (detailed implementation specs)
└── README.md          # For humans (usage examples, best practices)
```

**CLAUDE.md** includes:
- Implementation specifications
- Required functions/classes
- Error handling patterns
- Logging requirements
- Testing requirements (95%+ coverage)

**README.md** includes:
- Purpose and overview
- Usage examples
- Common issues and solutions
- Best practices
- Integration points

---

## Backend Architecture

### Layered Structure

```
HTTP Request
    ↓
Routes (HTTP handling)
    ↓
Controllers (orchestration)
    ↓
Services (business logic)
    ↓
Clients (external APIs) / Storage (data persistence)
    ↓
Models (data validation)
```

### Module Responsibilities

| Module | Purpose | Examples |
|--------|---------|----------|
| **routes** | HTTP endpoints, request/response | `/api/extract`, `/api/refine` |
| **controllers** | Orchestrate service calls | `extract_preferences()` |
| **services** | Business logic | NLP extraction, itinerary generation |
| **clients** | External API wrappers | Groq API, Google Maps (Phase 2) |
| **models** | Data structures, validation | `TripPreferences`, `Itinerary` |
| **storage** | Data persistence | JSON repos (Phase 1), MongoDB (Phase 2) |
| **utils** | Shared utilities | ID generation, date validation |
| **config** | Settings, env vars | API keys, app configuration |

---

## MVP Requirements Summary

### Non-Negotiable Features

1. **Budget Validation**: Daily budget minimum $50 CAD
2. **Required Fields**: starting_location, start_date, end_date, budget, interests (min 1), hours_per_day, transportation_modes (min 1), pace
3. **Pace Parameters**:
   - **Relaxed**: 2-3 activities/day, 90-120 min each, 20-min buffers
   - **Moderate**: 4-5 activities/day, 60-90 min each, 15-min buffers
   - **Packed**: 6+ activities/day, 30-60 min each, 5-min buffers

### Logging Standards

- **Format**: Structured JSON logs
- **Required Fields**: timestamp, level, name, message, request_id
- **Correlation**: request_id traces through all layers
- **Security**: Redact API keys, PII
- **Errors**: Include full traceback

### Testing Standards

- **Coverage**: 95%+ for all modules
- **Types**: Unit, integration, negative tests
- **Test Cases**: 5-10 concrete examples per module
- **Fixtures**: Mock external dependencies

---

## Getting Started

### 1. First Time Setup

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add GROQ_API_KEY

# Verify setup
python backend/diagnose.py

# Test imports
python backend/test_imports.py

# Run tests
pytest backend/tests/ -v
```

### 2. Development Workflow

```bash
# Start server
python backend/app.py

# Or with uvicorn
uvicorn backend.app:app --reload

# Run tests on change
pytest-watch backend/tests/
```

### 3. Common Tasks

**Adding a new endpoint**:
1. Read [Routes README](../routes/README.md)
2. Add endpoint to `routes/<domain>_routes.py`
3. Add tests to `tests/routes/test_<domain>_routes.py`
4. Update [Routes CLAUDE.md](../routes/CLAUDE.md)

**Adding a new service**:
1. Read [Services README](../services/README.md)
2. Create `services/<name>_service.py`
3. Add tests to `tests/services/test_<name>_service.py`
4. Update [Services CLAUDE.md](../services/CLAUDE.md)

**Updating models**:
1. Read [Models README](../models/README.md)
2. Modify `models/<name>.py`
3. Update validation logic
4. Add tests for new fields
5. Update [Models CLAUDE.md](../models/CLAUDE.md)

---

## Documentation Standards

### When to Update Documentation

**ALWAYS update docs when**:
- Adding new modules/files
- Changing public APIs
- Adding/removing dependencies
- Changing MVP requirements
- Adding new environment variables

**Update these files**:
- Relevant module README.md
- Relevant module CLAUDE.md
- This index (if adding new modules)
- DOCUMENTATION_STATUS.md

### Documentation Quality

All documentation must:
- Be accurate (reflect actual code)
- Include examples
- Specify test cases
- List assumptions and open questions
- Follow MVP requirements

---

## Testing Documentation

Each module's documentation includes test requirements:

- **Unit Tests**: 8-10 test cases per module
- **Integration Tests**: 3-5 end-to-end scenarios
- **Coverage Target**: 95%+

See individual module README.md files for specific test cases.

---

## Troubleshooting

### Common Issues

**Import errors**:
```bash
python backend/test_imports.py
```

**Environment issues**:
```bash
python backend/diagnose.py
```

**API connectivity**:
- Check GROQ_API_KEY in .env
- Test: `curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"`

**Test failures**:
```bash
# Run specific test
pytest backend/tests/services/test_nlp_extraction_service.py::test_extract_preferences -v

# Run with debugging
pytest --pdb backend/tests/
```

---

## Phase Roadmap

### Phase 1 (Current - MVP)
✅ NLP extraction service  
✅ Trip preference validation  
✅ JSON file storage  
✅ FastAPI routes  
✅ Comprehensive documentation

### Phase 2 (Planned)
- [ ] Itinerary generation
- [ ] MongoDB integration
- [ ] Google Maps API integration
- [ ] Weather API integration
- [ ] Budget tracking

### Phase 3 (Future)
- [ ] Apache Airflow scheduling
- [ ] Real-time adaptation
- [ ] User accounts
- [ ] Multi-trip planning

---

## Contributing

### Adding New Documentation

1. **Create module docs** following the pattern:
   - `<module>/CLAUDE.md` - Agent instructions
   - `<module>/README.md` - Human documentation

2. **Follow templates**:
   - See existing modules for structure
   - Include all required sections
   - Add test cases (95%+ coverage)

3. **Update this index**:
   - Add links to new docs
   - Update architecture diagram if needed
   - Update phase roadmap

4. **Validate**:
   - Check all links work
   - Verify code examples are accurate
   - Ensure MVP requirements are met

---

## Additional Resources

### External Documentation

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [Groq API Docs](https://console.groq.com/docs)
- [Pytest Docs](https://docs.pytest.org/)

### Internal Resources

- [Frontend Documentation](../../frontend/README.md)
- [Airflow DAGs](../../airflow/dags/)
- [Project README](../../README.md)
- [Implementation Guide](../../Kingston%20Trip%20Planner_%20MVP%20Implementation%20Guide%20(T.md)

---

## Contact

**Questions?**
- See individual module CLAUDE.md files for detailed specifications
- See individual module README.md files for usage examples
- See PRD files for product requirements

**Reporting Issues**:
- Document in Open Questions section of relevant module docs
- Update DOCUMENTATION_STATUS.md if blocking progress

---

**Last Updated**: 2026-02-07  
**Maintained By**: Backend Team  
**Total Docs**: 22 files (11 CLAUDE.md, 8 README.md, 4 PRD.md, 1 index)  
**Coverage**: All Phase 1 modules documented
