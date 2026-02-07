# PRD: app.py

**Product**: MonVoyage Kingston Trip Planner  
**Component**: Main FastAPI Application  
**Phase**: 1 (MVP - NLP Extraction)  
**Last Updated**: 2026-02-07

---

## 1. Purpose

Define the main FastAPI application entry point that:
- Initializes the web server
- Configures middleware (CORS, request ID generation)
- Registers API routes
- Sets up logging configuration
- Provides health check endpoint

---

## 2. Scope

### In Scope (Phase 1)
- FastAPI application initialization
- CORS middleware for frontend (localhost:3000)
- Request ID middleware for correlation logging
- Route registration (trip routes)
- Structured logging configuration
- Health check endpoint
- Error handling middleware

### Out of Scope (Phase 1)
- Authentication/authorization (Phase 2)
- Rate limiting (Phase 2)
- Database connection pooling (Phase 2)
- API versioning (Phase 3)
- GraphQL support (Phase 3)

---

## 3. Requirements

### Functional Requirements

**FR-1**: Application must initialize FastAPI with proper configuration
- **Acceptance Criteria**:
  - FastAPI app instance created
  - App metadata set (title, version, description)
  - Debug mode configurable via environment variable

**FR-2**: Application must configure CORS for frontend access
- **Acceptance Criteria**:
  - CORS middleware enabled
  - Allow origin: `http://localhost:3000` (development)
  - Allow credentials: true
  - Allow all methods and headers
  - Production origins configurable via environment

**FR-3**: Application must generate request IDs for all requests
- **Acceptance Criteria**:
  - Middleware generates UUID for each request
  - Request ID added to response headers
  - Request ID available in request context
  - Format: `req_YYYYMMDD_HHMMSS_uuid`

**FR-4**: Application must configure structured logging
- **Acceptance Criteria**:
  - JSON log format
  - Log level configurable (INFO default)
  - Logs include request_id, timestamp, level, message
  - Full tracebacks on errors
  - Sensitive data redacted (API keys, PII)

**FR-5**: Application must provide health check endpoint
- **Acceptance Criteria**:
  - `GET /api/health` returns 200
  - Response includes service name, version, status
  - Check external dependencies (Phase 2)

**FR-6**: Application must register trip routes
- **Acceptance Criteria**:
  - Trip router mounted at `/api`
  - All trip endpoints accessible
  - Endpoints: /extract, /refine, /health

### Non-Functional Requirements

**NFR-1**: Performance
- Server startup < 2 seconds
- Request overhead from middleware < 5ms
- Health check response time < 50ms

**NFR-2**: Reliability
- Graceful shutdown on SIGTERM/SIGINT
- Uncaught exceptions logged with full context
- Server restarts on critical errors (via Uvicorn)

**NFR-3**: Maintainability
- Clear separation of concerns (routes, middleware, config)
- Environment-specific configuration
- Easy to add new routes

---

## 4. Technical Specification

### File Structure
```
backend/
├── app.py                    # Main application (THIS FILE)
├── routes/
│   └── trip_routes.py       # Trip endpoints
├── config/
│   └── settings.py          # Configuration
└── utils/
    └── id_generator.py      # Request ID generation
```

### Implementation

**app.py**:
```python
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.routes.trip_routes import router as trip_router
from backend.config.settings import settings
from backend.utils.id_generator import generate_request_id

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("MonVoyage starting up")
    yield
    # Shutdown
    logger.info("MonVoyage shutting down")


# Create FastAPI app
app = FastAPI(
    title="MonVoyage Trip Planner",
    description="AI-powered Kingston trip itinerary generator",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests"""
    request_id = generate_request_id()
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# Error handling middleware
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error("Uncaught exception", extra={
        "request_id": request_id,
        "path": request.url.path
    }, exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id
            }
        }
    )


# Register routers
app.include_router(trip_router, prefix="/api")


# Health check (also in trip_routes, but good to have at root)
@app.get("/health")
async def root_health():
    return {
        "status": "healthy",
        "service": "MonVoyage Trip Planner",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Development only
        log_level="info"
    )
```

---

## 5. Testing Requirements

### Unit Tests (Minimum 8)

**Test Coverage**: 95%+

**Test Cases**:

1. **test_app_initialization**
   - Assert FastAPI app created
   - Assert title, version set correctly
   - Assert lifespan configured

2. **test_cors_middleware**
   - Make request from localhost:3000
   - Assert CORS headers present
   - Assert credentials allowed

3. **test_request_id_generation**
   - Make request
   - Assert X-Request-ID header in response
   - Assert format: `req_YYYYMMDD_HHMMSS_uuid`

4. **test_request_id_in_context**
   - Access request.state.request_id in endpoint
   - Assert request_id available

5. **test_health_endpoint**
   - GET /health
   - Assert 200 status
   - Assert response contains status, service, version

6. **test_api_health_endpoint**
   - GET /api/health
   - Assert 200 status
   - Assert response format

7. **test_global_error_handler**
   - Trigger uncaught exception
   - Assert 500 status
   - Assert error response format
   - Assert request_id in response

8. **test_routes_registered**
   - Assert /api/extract endpoint exists
   - Assert /api/refine endpoint exists

9. **test_startup_logging**
   - Start app
   - Assert "MonVoyage starting up" logged

10. **test_shutdown_logging**
    - Shutdown app
    - Assert "MonVoyage shutting down" logged

### Integration Tests (Minimum 3)

1. **test_full_request_flow**
   - Make POST to /api/extract
   - Assert request_id in response
   - Assert CORS headers present

2. **test_error_logging**
   - Trigger error
   - Assert error logged with request_id
   - Assert traceback included

3. **test_concurrent_requests**
   - Make 10 parallel requests
   - Assert each has unique request_id

---

## 6. Example Usage

### Starting the Server

```bash
# Development
python backend/app.py

# Production (via Uvicorn)
uvicorn backend.app:app --host 0.0.0.0 --port 8000

# With workers (production)
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Health Check

```bash
curl http://localhost:8000/health
# {"status":"healthy","service":"MonVoyage Trip Planner","version":"1.0.0"}
```

### Request ID Example

```bash
curl -v http://localhost:8000/api/health
# Response headers include:
# X-Request-ID: req_20260207_143052_abc123...
```

---

## 7. Open Questions

1. **Production CORS**: What frontend URLs to allow in production?
2. **Rate Limiting**: Should we implement rate limiting in Phase 1?
3. **API Versioning**: When to introduce /v1, /v2 endpoints?
4. **Monitoring**: What metrics to expose (Prometheus, StatsD)?

---

## 8. Future Enhancements

### Phase 2
- [ ] Authentication middleware (JWT)
- [ ] Rate limiting (per-user, per-IP)
- [ ] Database connection pool initialization
- [ ] Redis session management
- [ ] Sentry error tracking

### Phase 3
- [ ] API versioning (/api/v1, /api/v2)
- [ ] GraphQL endpoint
- [ ] WebSocket support (real-time updates)
- [ ] Metrics endpoint (/metrics)
- [ ] Admin dashboard

---

## 9. Acceptance Criteria Summary

✅ **DONE**: FastAPI app initializes  
✅ **DONE**: CORS configured for localhost:3000  
✅ **DONE**: Request IDs generated for all requests  
✅ **DONE**: Structured logging configured  
✅ **DONE**: Health check endpoint at /health  
✅ **DONE**: Trip routes registered at /api  
✅ **DONE**: Global error handler logs and returns 500  
✅ **DONE**: Tests achieve 95%+ coverage

---

**Maintained By**: Backend Team  
**Reviewed By**: Technical Lead  
**Status**: Phase 1 - Ready for Implementation
