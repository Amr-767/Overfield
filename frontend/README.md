# AgroSpace Quest — Frontend

React + TypeScript + Vite foundation (Phase 1C).

## Setup

```powershell
cd frontend
copy .env.example .env
npm install
```

`VITE_API_BASE_URL` must point at the Django API (default `http://127.0.0.1:8000`).
Only public values belong in Vite env files.

## Run

With Docker infra and Django already running:

```powershell
npm run dev
```

Open `http://127.0.0.1:5173/`.

## Build

```powershell
npm run build
npm run preview
```

## Lint and tests

```powershell
npm run lint   # oxlint
npm test       # vitest (API client + health connectivity unit tests)
```

The health connectivity check calls `GET /api/v1/health/` on the Django API and
renders loading, connected, and error states. It requires the backend to be
running (see the repository root README).
