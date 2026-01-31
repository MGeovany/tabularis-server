import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1 import auth, convert, history, usage
from app.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger()

app = FastAPI(
    title="Tabularis API",
    description="Backend for Tabular — PDF to Excel conversion with Supabase Auth",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request (method, path, status, duration)."""
    start = time.perf_counter()
    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        from fastapi import HTTPException
        if not isinstance(exc, HTTPException):
            logger.exception(
                "%s %s -> 500 (%.1f ms) | %s",
                request.method,
                request.url.path,
                duration_ms,
                exc,
            )
        raise


@app.on_event("startup")
def startup():
    logger.info("Tabularis API starting")


@app.get("/health")
def health():
    logger.info("GET /health")
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log unhandled exceptions (not HTTPException) and return 500."""
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception(
        "Internal Server Error: %s %s | %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(convert.router, prefix="/api/v1", tags=["convert"])
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(usage.router, prefix="/api/v1", tags=["usage"])
