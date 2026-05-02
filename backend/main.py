import sys
from pathlib import Path

from fastapi import Body, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.database import init_db
from backend.routes import bot, dashboard, settings
from backend.services.bot_service import sync_bot_state_from_storage

app = FastAPI(title="PulseX Trader API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://10.54.50.228:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    init_db()
    sync_bot_state_from_storage()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=200, content={"success": False, "error": str(exc)})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=200, content={"success": False, "error": "Invalid request payload."})


@app.middleware("http")
async def debug_request_logging(request: Request, call_next):
    print("Request received")
    print(f"{request.method} {request.url.path}")
    return await call_next(request)


@app.get("/")
async def root() -> dict:
    return {"success": True, "name": "PulseX Trader", "status": "online", "error": None}


@app.get("/api/health")
async def health() -> dict:
    return {"success": True, "status": "healthy", "error": None}


app.include_router(settings.router)
app.include_router(bot.router)
app.include_router(dashboard.router)
