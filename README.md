# PulseX Trader

PulseX Trader is a local FastAPI + React crypto trading bot dashboard with paper trading, encrypted API credentials, SQLite logging, and a stable signal engine for BTCUSDT, ETHUSDT, and SOLUSDT.

## Features

- FastAPI backend with CORS preconfigured for Vite.
- Fernet credential encryption that auto-generates a temporary key if one is missing or invalid.
- SQLite storage for credentials, settings, decisions, trades, PnL, and bot events.
- Multi-coin EMA 9 / EMA 21 / RSI 14 strategy with confidence scoring.
- Risk controls: 10% balance allocation, 0.5% stop loss, 1% take profit, max one trade, 5-minute cooldown, max 5 trades per day, and 2% daily loss stop.
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
