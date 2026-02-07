# MonVoyage Backend Documentation Guide

**Created**: 2026-02-07  
**Total Files**: 22 documentation files  
**Purpose**: Complete backend documentation for MonVoyage Kingston Trip Planner MVP

---

## Overview

This guide describes all documentation files created for the MonVoyage backend. Each file serves a specific purpose in helping developers (both human and AI) understand, implement, and maintain the backend system.

---

## Documentation Files Created

### 1. Core Backend Documentation

#### `backend/CLAUDE_EMBEDDED.md`
**What it does**: Defines the foundational MVP operational rules for the entire backend  
**Contribution to project**:
- Centralizes all non-negotiable MVP requirements ($50/day budget, pace parameters)
- Establishes logging standards (structured JSON, correlation IDs)
- Defines testing requirements (95%+ coverage)
- Provides MongoDB schema specifications for Phase 2
- Referenced by all module-level CLAUDE.md files to ensure consistency

**Key sections**: Mandatory features, validation rules, logging standards, error handling, testing requirements

---

### 2. Module Documentation (Config)

#### `backend/config/CLAUDE.md`
**What it does**: Agent instructions for implementing the configuration module
**Contribution to project**:
- Specifies how to load environment variables (.env file handling)
- Defines settings structure and validation for both Gemini (primary) and Groq (fallback) LLMs
- Ensures API keys are never committed to version control
- Provides exact implementation spec for settings.py (Gemini config merged here; no separate gemini.py)

**Key sections**: Settings class specification, environment variables, validation logic, security rules

#### `backend/config/README.md`
**What it does**: Human-oriented documentation for the config module  
**Contribution to project**:
- Guides developers on setting up their .env file
- Explains each configuration option
- Provides troubleshooting for common issues (missing API key, wrong format)
- Shows example usage and best practices

**Key sections**: Setup instructions, environment variables reference, common issues, API reference

---

### 3. Module Documentation (Models)

#### `backend/models/CLAUDE.md`
**What it does**: Agent instructions for implementing data models (TripPreferences)  
**Contribution to project**:
- Defines complete TripPreferences dataclass with all fields
- Specifies validation logic ($50/day enforcement, date validation)
- Implements completeness scoring algorithm
- Ensures data consistency across the application

**Key sections**: TripPreferences specification, validation methods, completeness scoring, test cases

#### `backend/models/README.md`
**What it does**: Human-oriented documentation for data models  
**Contribution to project**:
- Explains validation rules in plain language
- Shows example trip preferences and validation results
- Documents completeness scoring calculation
- Lists 20+ test cases for comprehensive validation

**Key sections**: Data structures, validation rules, completeness scoring, usage examples, test cases

---

### 4. Module Documentation (Services)

#### `backend/services/CLAUDE.md`
**What it does**: Agent instructions for implementing business logic services (NLP extraction)
**Contribution to project**:
- Specifies NLPExtractionService implementation
- Defines Gemini API (primary) / Groq API (fallback) integration patterns
- Establishes conservative extraction rules (never guess)
- Provides prompt engineering guidelines for LLM

**Key sections**: Service specification, Gemini/Groq integration, extraction logic, refinement logic, error handling

#### `backend/services/README.md`
**What it does**: Human-oriented documentation for services layer  
**Contribution to project**:
- Explains NLP extraction process flow
- Shows example inputs and outputs
- Documents expected response times (800ms-1.5s)
- Provides debugging guidance for extraction issues

**Key sections**: NLP extraction overview, usage examples, performance metrics, common issues

---

### 5. Module Documentation (Clients)

#### `backend/clients/CLAUDE.md`
**What it does**: Agent instructions for implementing external API clients (Gemini primary, Groq fallback)
**Contribution to project**:
- Specifies GeminiClient (primary) and GroqClient (fallback) wrappers
- Defines retry logic with exponential backoff (1s, 2s, 4s)
- Establishes error handling patterns (retry 5xx, don't retry 4xx)
- Ensures API keys are redacted in logs

**Key sections**: GeminiClient specification, GroqClient specification, retry strategy, error handling, API key security

#### `backend/clients/README.md`
**What it does**: Human-oriented documentation for API clients (Gemini primary, Groq fallback)
**Contribution to project**:
- Guides developers on configuring Gemini (primary) and Groq (fallback) API access
- Explains retry strategy and when it triggers
- Documents error types and handling
- Shows expected response times and timeouts

**Key sections**: Client overview, Gemini/Groq configuration, retry configuration, error handling, usage examples

---

### 6. Module Documentation (Utils)

#### `backend/utils/CLAUDE.md`
**What it does**: Agent instructions for implementing utility functions  
**Contribution to project**:
- Specifies IDGenerator for creating unique IDs
- Defines ID prefix conventions (trip_, activity_, req_)
- Establishes request correlation ID pattern
- Plans date validation utilities (Phase 2)

**Key sections**: ID generation, UUID format, request correlation, date utilities

#### `backend/utils/README.md`
**What it does**: Human-oriented documentation for utilities  
**Contribution to project**:
- Explains ID generation patterns and why they're used
- Shows how request IDs enable tracing through logs
- Documents date format standards (ISO-8601, UTC)
- Provides practical examples of utility usage

**Key sections**: ID generation examples, request correlation, date handling, best practices

---

### 7. Module Documentation (Routes)

#### `backend/routes/CLAUDE.md`
**What it does**: Agent instructions for implementing HTTP routes  
**Contribution to project**:
- Specifies all FastAPI endpoint implementations
- Defines request/response models (Pydantic)
- Establishes HTTP status code usage (200, 400, 500, 503)
- Implements request ID middleware

**Key sections**: Endpoint specifications, request/response models, error handling, middleware

#### `backend/routes/README.md`
**What it does**: Human-oriented API documentation  
**Contribution to project**:
- Documents all API endpoints with curl examples
- Explains HTTP status codes and error formats
- Shows CORS configuration for frontend
- Provides integration examples in Python/JavaScript

**Key sections**: Endpoint documentation, error responses, CORS setup, usage examples, test cases

---

### 8. Module Documentation (Controllers)

#### `backend/controllers/CLAUDE.md`
**What it does**: Agent instructions for implementing controllers  
**Contribution to project**:
- Specifies TripController orchestration logic
- Defines controller responsibilities (orchestrate, not implement)
- Establishes request ID propagation pattern
- Ensures controllers remain thin (20-50 lines per method)

**Key sections**: Controller specification, orchestration patterns, request ID flow, error handling

#### `backend/controllers/README.md`
**What it does**: Human-oriented controller documentation  
**Contribution to project**:
- Explains controller pattern and responsibilities
- Shows proper separation of concerns (routes → controllers → services)
- Documents request/response transformation
- Provides anti-patterns to avoid (business logic in controllers)

**Key sections**: Controller pattern, response format, error handling, common issues, best practices

---

### 9. Module Documentation (Storage)

#### `backend/storage/CLAUDE.md`
**What it does**: Agent instructions for implementing data persistence  
**Contribution to project**:
- Specifies repository pattern for data access
- Defines JSON file storage for Phase 1
- Plans MongoDB migration for Phase 2
- Establishes consistent interface (save, load, delete, list_all)

**Key sections**: Repository specifications, JSON storage, MongoDB plans, error handling

#### `backend/storage/README.md`
**What it does**: Human-oriented storage documentation  
**Contribution to project**:
- Explains repository pattern benefits (abstraction, testability)
- Documents JSON file format and structure
- Shows Phase 2 MongoDB migration path
- Provides storage usage examples

**Key sections**: Repository pattern, file storage, MongoDB migration, usage examples, test cases

---

### 10. Product Requirements Documents (PRDs)

#### `backend/docs/app.PRD.md`
**What it does**: Complete product requirements for app.py (main FastAPI application)  
**Contribution to project**:
- Defines FastAPI initialization requirements
- Specifies CORS middleware configuration
- Establishes request ID generation middleware
- Documents logging configuration and health check endpoint
- Provides 10 test cases and acceptance criteria

**Key sections**: Purpose, requirements, technical spec, testing, examples, acceptance criteria

#### `backend/docs/diagnose.PRD.md`
**What it does**: Product requirements for diagnose.py (system diagnostics)  
**Contribution to project**:
- Specifies environment validation script
- Defines checks for Python version, packages, API connectivity
- Establishes clear troubleshooting output format
- Enables pre-development environment verification
- Useful for both developers and CI/CD pipelines

**Key sections**: Purpose, requirements, implementation, test cases, examples

#### `backend/docs/test_imports.PRD.md`
**What it does**: Product requirements for test_imports.py (import validation)  
**Contribution to project**:
- Specifies fast import validation script (< 2 seconds)
- Catches syntax errors before running full test suite
- Enables CI/CD fast-fail mechanism
- Provides clear error messages for debugging
- Complements pytest (fast checks before comprehensive tests)

**Key sections**: Purpose, requirements, implementation, CI/CD integration, examples

#### `backend/docs/requirements.PRD.md`
**What it does**: Product requirements for requirements.txt (dependencies)  
**Contribution to project**:
- Documents all Python dependencies and their purposes
- Specifies version constraints and upgrade strategy
- Explains why each package is needed
- Plans Phase 2/3 dependencies (MongoDB, Celery, Sentry)
- Ensures reproducible builds

**Key sections**: Dependencies list, version constraints, installation, upgrade strategy, security

---

### 11. Documentation Index

#### `backend/docs/README.md`
**What it does**: Master index for all backend documentation  
**Contribution to project**:
- Provides single entry point to all documentation
- Organizes docs by audience (humans vs AI agents)
- Summarizes backend architecture and module responsibilities
- Lists MVP requirements and development workflow
- Includes troubleshooting guide and phase roadmap

**Key sections**: Quick links, architecture overview, MVP requirements, getting started, troubleshooting

---

## How These Files Work Together

### For Human Developers

1. **Start here**: `backend/docs/README.md` (documentation index)
2. **Understand MVP**: `backend/CLAUDE_EMBEDDED.md` (operational rules)
3. **Learn modules**: Read module README.md files (usage examples)
4. **Implement features**: Follow PRD files (requirements and specs)
5. **Troubleshoot**: Use diagnose.py and test_imports.py

### For AI Agents

1. **Load context**: `backend/CLAUDE_EMBEDDED.md` (MVP rules)
2. **Implement module**: Read module CLAUDE.md (exact specifications)
3. **Validate**: Check tests achieve 95%+ coverage
4. **Update docs**: Keep CLAUDE.md and README.md in sync with code

### For CI/CD Pipelines

1. **Fast checks**: Run `test_imports.py` (< 2s)
2. **Environment**: Run `diagnose.py` (verify setup)
3. **Full tests**: Run `pytest` (comprehensive validation)
4. **Coverage**: Check 95%+ coverage threshold

---

## Documentation Quality Standards

All files follow these standards:

✅ **Accuracy**: Reflects actual code and requirements  
✅ **Completeness**: Includes all necessary information  
✅ **Examples**: Provides concrete usage examples  
✅ **Test Cases**: Specifies 5-10+ test cases per module  
✅ **Assumptions**: Lists assumptions and open questions  
✅ **MVP Consistency**: Aligns with $50/day budget, pace parameters, required fields  
✅ **Logging**: Follows structured JSON logging with correlation IDs  
✅ **Testing**: Targets 95%+ code coverage

---

## File Organization

```
backend/
├── CLAUDE_EMBEDDED.md           # Core operational rules
├── docs/
│   ├── README.md                # Documentation index
│   ├── app.PRD.md              # FastAPI app requirements
│   ├── diagnose.PRD.md         # Diagnostics requirements
│   ├── test_imports.PRD.md     # Import test requirements
│   └── requirements.PRD.md     # Dependencies requirements
├── config/
│   ├── CLAUDE.md               # Agent instructions
│   └── README.md               # Human documentation (note: gemini.py removed, merged into settings.py)
├── models/
│   ├── CLAUDE.md               # Agent instructions
│   └── README.md               # Human documentation
├── services/
│   ├── CLAUDE.md               # Agent instructions
│   └── README.md               # Human documentation
├── controllers/
│   ├── CLAUDE.md               # Agent instructions
│   └── README.md               # Human documentation
├── routes/
│   ├── CLAUDE.md               # Agent instructions
│   └── README.md               # Human documentation
├── clients/
│   ├── CLAUDE.md               # Agent instructions
│   └── README.md               # Human documentation
├── utils/
│   ├── CLAUDE.md               # Agent instructions
│   └── README.md               # Human documentation
└── storage/
    ├── CLAUDE.md               # Agent instructions
    └── README.md               # Human documentation
```

---

## Benefits to the Project

### 1. **Consistency**
- All modules follow same patterns
- MVP requirements enforced everywhere
- Logging and testing standards unified

### 2. **Onboarding**
- New developers can understand system quickly
- AI agents have exact specifications
- Clear examples reduce questions

### 3. **Maintainability**
- Documentation stays with code
- Changes tracked in version control
- Easy to update as system evolves

### 4. **Quality**
- 95%+ test coverage requirement
- Concrete test cases prevent regressions
- Error handling patterns standardized

### 5. **Collaboration**
- Human and AI developers share same docs
- Clear separation of concerns
- Well-defined interfaces between modules

### 6. **Debugging**
- Diagnostic tools (diagnose.py, test_imports.py)
- Troubleshooting guides in each README
- Request ID correlation for tracing

---

## Next Steps

### Using This Documentation

1. **Read the index**: Start at `backend/docs/README.md`
2. **Understand MVP**: Review `backend/CLAUDE_EMBEDDED.md`
3. **Explore modules**: Read module README.md files
4. **Implement code**: Follow CLAUDE.md specifications
5. **Verify setup**: Run `diagnose.py` and `test_imports.py`

### Keeping Documentation Updated

When you:
- Add new modules → Create CLAUDE.md + README.md
- Change APIs → Update relevant module docs
- Add dependencies → Update requirements.PRD.md
- Change MVP rules → Update CLAUDE_EMBEDDED.md

---

## Summary

This documentation system provides:

- **22 comprehensive files** covering all backend aspects
- **Dual format** (agent instructions + human guides)
- **Complete specs** for 8 modules + 4 key files
- **95%+ test coverage** requirements
- **MVP consistency** throughout
- **Clear standards** for logging, testing, error handling

**Result**: A well-documented, maintainable backend ready for implementation by both human and AI developers.

---

**Created By**: Backend Documentation Team  
**Last Updated**: 2026-02-07  
**Status**: Phase 1 - Complete ✅
