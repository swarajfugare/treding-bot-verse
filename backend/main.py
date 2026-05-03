import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

sys.path.append(str(Path(__file__).resolve().parent))

from database import init_db
from routes import bot, dashboard, settings
from services.bot_service import sync_bot_state_from_storage

app = FastAPI(title="PulseX Trader API", version="1.0.0")
PORT = int(os.environ.get("PORT", 8000))
print(f"PulseX Trader backend booting on PORT={PORT}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    print("PulseX Trader startup: initializing database")
    try:
        init_db()
        sync_bot_state_from_storage()
        print("PulseX Trader startup: ready")
    except Exception as exc:
        print(f"PulseX Trader startup handled error: {exc}")


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
    return {"status": "ok"}


app.include_router(settings.router)
app.include_router(bot.router)
app.include_router(dashboard.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
