# PulseX Trader

PulseX Trader is a local FastAPI + React crypto trading bot dashboard with paper trading, encrypted API credentials, SQLite logging, and a stable signal engine for BTCUSDT, ETHUSDT, and SOLUSDT.

## Features

- FastAPI backend with CORS preconfigured for Vite.
- Fernet credential encryption that auto-generates a temporary key if one is missing or invalid.
- SQLite storage for credentials, settings, decisions, trades, PnL, and bot events.
- Multi-coin trend-following strategy using EMA50/EMA200 trend, RSI 14, MACD confirmation, 1m + 5m alignment, and volume filters.
- Risk controls: 10% balance allocation, 1.5% stop loss, 3% take profit, max one trade, 10-minute cooldown, max 5 trades per day, and configurable daily loss stop.
- React dashboard with bot control, active trade, recent trades, decision panel, credentials, and paper-trading toggle.

## Backend Setup

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

If `FERNET_KEY` is blank, the server generates a key, prints it, saves it to `backend/.env`, and continues without crashing.

Strategy thresholds are configurable in `.env` with `STRATEGY_MIN_CONFIDENCE`, `STRATEGY_MIN_VOLUME`, `STRATEGY_MIN_EMA_DISTANCE_PCT`, `STRATEGY_STOP_LOSS_PCT`, and `STRATEGY_TAKE_PROFIT_PCT`.

## Frontend Setup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open [http://10.54.50.228:5173](http://10.54.50.228:5173).

The frontend uses `VITE_API_URL` from `frontend/.env`, for example:

```bash
VITE_API_URL=http://10.54.50.228:8000
```

PulseX Trader does not restrict API credentials by local IP. If an exchange account has IP restrictions enabled, use your exchange account's public outbound IP allowlist or remove that restriction for development.

## Render Backend Deployment

Recommended deployment: use Docker on Render. This bypasses Render's native Python auto-version selection and pins Python to `3.10.13`.

Render settings:

- Language: `Docker`
- Root Directory: leave blank
- Dockerfile Path: `./Dockerfile`
- Docker Context: `.`

The backend includes:

- root-level `Dockerfile` and `.dockerignore` for reliable Render Docker deploys
- root-level `.python-version`, `runtime.txt`, `requirements.txt`, and `Procfile` as a fallback if Render is pointed at the repository root
- `runtime.txt` with `python-3.10.13`
- `requirements.txt` with stable FastAPI, Pydantic, pandas, and numpy pins
- `Procfile` with the production Uvicorn command
- `render.yaml` configured for Docker deployment

Do not add `pyproject.toml` or `poetry.lock` unless you intentionally want Render to switch back to Poetry.

If the Render deploy log still says `Using Python version 3.14.3`, that deploy is not using Docker. Create a new Docker service or sync the Blueprint. The Docker build log should show `FROM python:3.10.13-slim`.

## Koyeb Backend Deployment

Koyeb is a good free alternative for this backend because it supports Dockerfile-based web services and has a free web Service.

Control panel setup:

- Create Web Service
- Select GitHub repository
- Builder: `Dockerfile`
- Branch: `main`
- Dockerfile Path: `./Dockerfile`
- Exposed Port: `10000`
- Route: `/`

Environment variables:

```bash
FERNET_KEY=your_fernet_key
DATABASE_PATH=./pulsex.db
PAPER_TRADING=true
PAPER_BALANCE=10000
DELTA_API_URL=https://api.india.delta.exchange
DELTA_USD_INR_RATE=85
DELTA_FIXED_USD_INR=true
```

After Koyeb deploys, set your frontend `VITE_API_URL` to the public `.koyeb.app` backend URL.

## Vercel Frontend Deployment

Set the Vercel root directory to `frontend` and configure:

```bash
VITE_API_URL=https://your-render-service.onrender.com
```

Build command:

```bash
npm run build
```

Output directory:

```bash
dist
```

## Main API Endpoints

- `GET /api/health`
- `POST /api/settings/credentials`
- `GET /api/settings/credentials`
- `POST /api/settings/credentials/test`
- `POST /api/settings/paper`
- `POST /api/bot`
- `GET /api/bot/status`
- `GET /api/bot/decision`
- `GET /api/dashboard`
- `GET /api/trades`

Credential requests accept either:

```json
{ "api_key": "value", "api_secret": "value" }
```

or:

```json
{ "key": "value", "secret": "value" }
```
