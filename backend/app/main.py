import time
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.dependencies import get_db
from app.features.candidates.router import router as candidates_router
from app.features.evaluations.router import router as evaluations_router
from app.features.imports.router import router as imports_router
from app.features.matching.embeddings import warm_up_embeddings
from app.features.matching.router import router as matching_router
from app.features.mentors.router import router as mentors_router
from app.features.projects.router import router as projects_router

# 1. Logging Setup Configuration
shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.format_exc_info,
    structlog.processors.TimeStamper(fmt="iso"),
]

if settings.ENV == "production":
    processors = [
        *shared_processors,
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]
else:
    processors = [
        *shared_processors,
        structlog.processors.dict_tracebacks,
        structlog.dev.ConsoleRenderer(colors=True),
    ]

structlog.configure(
    processors=processors,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()


# 2. Scaffolding FastAPI Application
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Preload the embedding model in a background thread so the first matching
    # request doesn't pay the ~30s CPU load (which used to also block the
    # event loop, freezing every in-flight request while it loaded).
    warm_up_embeddings()
    yield


app = FastAPI(
    title="ProjectMatchAI API",
    version="0.1.0",
    description="Backend API for ProjectMatchAI bulk intake and matching",
    lifespan=lifespan,
)

# 3. CORS Configuration Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 4. Request Logging & Correlation ID Middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter()
        log.info("http.request_received", method=request.method, path=request.url.path)

        try:
            response: Response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000
            response.headers["X-Request-ID"] = request_id
            log.info(
                "http.request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(process_time, 2),
            )
            return response
        except Exception as e:
            process_time = (time.perf_counter() - start_time) * 1000
            log.error(
                "http.request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_ms=round(process_time, 2),
                exc_info=True,
            )
            raise


app.add_middleware(LoggingMiddleware)


# 5. Global Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    log.warning(
        "http.exception",
        path=request.url.path,
        status_code=exc.status_code,
        detail=exc.detail,
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    log.warning("validation.error", path=request.url.path, errors=exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled.error", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


# 6. API Routing and Health Check Endpoints
app.include_router(imports_router)
app.include_router(candidates_router)
app.include_router(evaluations_router)
app.include_router(mentors_router)
app.include_router(projects_router)
app.include_router(matching_router)


@app.get("/api/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    try:
        # Perform query to verify database connection
        await db.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "database": "connected",
                "environment": settings.ENV,
                "llm": {
                    "enabled": settings.LLM_ENABLED,
                    "provider": settings.LLM_PROVIDER,
                    "configured": settings.llm_is_configured(),
                },
            },
        )
    except Exception as e:
        log.error("health.check_failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "disconnected",
                "environment": settings.ENV,
            },
        )
