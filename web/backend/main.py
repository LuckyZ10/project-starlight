import logging
import time
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import init_db
from routers import auth, cartridges, learning

logger = logging.getLogger("starlight")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("✨ Starlight backend ready")
    yield


app = FastAPI(title="Starlight", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handlers ──────────────────────────────────────

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle business logic validation errors."""
    logger.warning("ValueError on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "type": "validation_error"},
    )


@app.exception_handler(FileNotFoundError)
async def not_found_handler(request: Request, exc: FileNotFoundError):
    """Handle missing resource errors."""
    logger.warning("FileNotFoundError on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc), "type": "not_found"},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions."""
    logger.error(
        "Unhandled exception on %s: %s\n%s",
        request.url.path, exc, traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again.", "type": "server_error"},
    )


# ── Request Logging Middleware ─────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Request failed: %s %s", request.method, request.url.path)
        raise
    elapsed = (time.time() - start) * 1000
    if response.status_code >= 400:
        logger.warning(
            "%s %s → %d (%.0fms)",
            request.method, request.url.path, response.status_code, elapsed,
        )
    else:
        logger.debug(
            "%s %s → %d (%.0fms)",
            request.method, request.url.path, response.status_code, elapsed,
        )
    return response


app.include_router(auth.router)
app.include_router(cartridges.router)
app.include_router(learning.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
