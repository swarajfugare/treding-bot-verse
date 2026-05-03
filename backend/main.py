import os
import sys
import time
import logging
import uvicorn
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# -------------------------
# PATH FIX
# -------------------------
sys.path.append(str(Path(__file__).resolve().parent))

# -------------------------
# LOGGING
# -------------------------
logging.basicConfig(level=logging.INFO)

# -------------------------
# APP INIT (ONLY ONCE)
# -------------------------
app = FastAPI(title="PulseX Trader API", version="1.0.0")

# -------------------------
# IMPORTS (AFTER APP INIT)
# -------------------------
from database import init_db
from routes import bot, dashboard, settings
from services.bot_service import sync_bot_state_from_storage

# -------------------------
# CORS
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change later to your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# STARTUP (SAFE)
# -------------------------
@app.on_event("startup")
async def startup():
    logging.info("🚀 Starting backend...")

    try:
        init_db()
        sync_bot_state_from_storage()
        logging.info("✅ Backend ready")
    except Exception as exc:
        logging.error(f"Startup error handled: {exc}")

# -------------------------
# ERROR HANDLERS
# -------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={"success": False, "error": str(exc)},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=200,
        content={"success": False, "error": "Invalid request payload."},
    )

# -------------------------
# REQUEST LOGGING
# -------------------------
@app.middleware("http")
async def debug_request_logging(request: Request, call_next):
    start = time.perf_counter()

    logging.info(f"{request.method} {request.url.path}")

    response = await call_next(request)

    duration = round((time.perf_counter() - start) * 1000, 2)
    logging.info(f"{request.method} {request.url.path} {response.status_code} {duration}ms")

    return response

# -------------------------
# ROUTES
# -------------------------
@app.get("/")
def root():
    return {
        "success": True,
        "name": "PulseX Trader",
        "status": "online",
    }

@app.get("/api/health")
def health():
    return {"status": "ok"}

# Include routers
app.include_router(settings.router)
app.include_router(bot.router)
app.include_router(dashboard.router)

# -------------------------
# RUN SERVER (RAILWAY FIX)
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logging.info(f"Running on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port)
