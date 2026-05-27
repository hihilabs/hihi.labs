# worker_bundle/

Untracked from git (contains config.env with secrets).

## What is it
Standalone pull-worker for the Workers system (`/workers/` in the app).
Runs on remote machines (e.g. OmegaMEP workstations, GPU rigs) and polls
hihilabs.xyz/workers/ for queued jobs.

## Files
- `worker.py`         — main worker loop (Rich TUI, job dispatcher)
- `docker-compose.yml` — Docker packaging for deployment to client sites
- `config.env`        — API keys + worker identity (NOT in git — keep it that way)
- `requirements.txt`  — Python deps

## Supported job types
- `hvac_extract`  — OCR + HVAC nameplate detection from CompanyCam photos
- `library_sync`  — bulk photo download to local cache
- `ai_task`       — Loyd AI inference (cloud or local GPU)

## Deploying to a new machine
```bash
cp config.env.example config.env   # fill in WORKER_KEY, HUB_URL, WORKER_ID
docker compose up -d
```

## config.env should contain
```
WORKER_KEY=...      # from /workers/ admin panel
HUB_URL=https://hihilabs.xyz
WORKER_ID=...       # registered worker node ID
```
