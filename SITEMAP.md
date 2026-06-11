# HiHi Labs — Project Sitemap
> For Lloyd. Last updated: 2026-06-08
> Server: **Tokyo7** — `tokyo7.local` / `192.168.0.28` (Unraid, LAN only)
> VPS: `66.175.239.235` — `root@66.175.239.235` (public, always reachable)

---

## Infrastructure

| Thing | Value |
|---|---|
| Unraid UI | https://tokyo7.local:444 |
| Traefik dashboard | https://tokyo7.local:8080 (if enabled) |
| VPS SSH | `ssh root@66.175.239.235` |
| Unraid SSH (LAN) | `ssh root@tokyo7.local` |
| Cloudflare zone | `communityplaylist.com` — Zone ID `a87f91c2fa5aa9591c45c8879196eb59` |

---

## Projects

### 1. HiHi Labs — `hihilabs.xyz`
The main hub app. Django. Manages clients, projects, proposals, contracts, ops, AI tools, servers, wiki, modules.

| | |
|---|---|
| **Live URL** | https://hihilabs.xyz |
| **Alt domain** | https://hihilabs.communityplaylist.com |
| **Expo subdomain** | https://expo.hihilabs.xyz |
| **Compose stack** | `HIHILABS` — auto-start ON |
| **Local appdata** | `/mnt/user/appdata/hihilabs` |
| **GitHub** | `git@github-hihi-labs:hihilabs/hihi.labs.git` |
| **VPS app root** | `/var/www/vhosts/communityplaylist.com/tokyo7.communityplaylist.com/` |
| **DB** | SQLite (`db.sqlite3`) via named Docker volume `hihilabs_hihilabs_db` |
| **Status** | Running on Tokyo7 + mirrored on VPS |

Key apps inside hihilabs: `clients`, `projects`, `proposals`, `contracts`, `services`, `sound`, `claude_ai`, `servers`, `wiki`, `modules`, `ops`, `workers`, `billing`, `subscriptions`, `pepperjuice`, `portal`, `tickets`, `whiteboards`

---

### 2. Community Playlist — `communityplaylist.com`
Music event/playlist community app. Django + SQLite.

| | |
|---|---|
| **Live URL** | https://local.communityplaylist.com (local Unraid instance) |
| **Compose stack** | `CP` — auto-start OFF |
| **Local appdata** | `/mnt/user/appdata/cp-local` |
| **GitHub (app)** | `git@github.com:khildren/cp-worker.git` (worker) |
| **Worker appdata** | `/mnt/user/appdata/cp-worker` |
| **DB** | SQLite (`db.sqlite3`) |
| **Status** | Running locally, VPS hosts prod |

> cp-local-wiki-cron is crash-looping — Python bug in `wiki_cron_runner.py` (missing `import os`). Lives on VPS — fix there.

---

### 3. Lost Signal — `lostsignal.communityplaylist.com`
Portfolio/music site. Django + Postgres.

| | |
|---|---|
| **Live URL** | https://lostsignal.communityplaylist.com |
| **Compose stack** | `LOSTSIGNAL` — auto-start OFF |
| **Local appdata** | `/mnt/user/appdata/lostsignal` |
| **GitHub** | `git@github-lostsignal:khildren/lostsignal.git` |
| **DB** | Postgres 16 (`pgdata/`) |
| **Cron** | Nightly `sync_portfolio` + `sync_youtube` at 3am |
| **Status** | Stopped locally (Exited 255) |

---

### 4. Blue Solutions — `blue.communityplaylist.com`
Portfolio/agency site. Django + Postgres.

| | |
|---|---|
| **Live URL** | https://blue.communityplaylist.com |
| **Compose stack** | `BLUESOLUTIONS` — auto-start OFF |
| **Local appdata** | `/mnt/user/appdata/bluesolutions` |
| **GitHub** | `git@github-portfolio-blue:khildren/portfolio-blue.git` |
| **VPS git remote** | `root@66.175.239.235:/var/repos/blue.git` |
| **DB** | Postgres 16 (`pgdata/`) |
| **Status** | Stopped locally |

---

### 5. Mile High's Finest / Apothecary — `milehighsfinest.shop`
E-commerce / apothecary shop. Django + Postgres + Redis. Has self-hosted GitHub Actions runner.

| | |
|---|---|
| **Live URLs** | https://milehighsfinest.shop · https://apothecary.communityplaylist.com |
| **Compose stack** | `MILEHIGH` — auto-start OFF |
| **Local appdata** | `/mnt/user/appdata/milehigh` |
| **GitHub** | `https://github.com/khildren/apothecary` |
| **Local port** | `8194` → app |
| **DB** | Postgres 16 (`pgdata/`) + Redis |
| **Status** | Running on Tokyo7 (`milehigh`, `milehigh-db`, `milehigh-redis`) |

> GitHub runner token expires ~1hr after generation. Regenerate at: https://github.com/khildren/apothecary/settings/actions/runners/new

---

### 6. OmegaMEP — `omegamep.com` / `omegamep.communityplaylist.com`
MEP (music/events/playlists) platform. Two sub-deployments.

| | |
|---|---|
| **Live URLs** | https://omegamep.com (→ redirects to communityplaylist subdomain) · https://omegamep.communityplaylist.com |
| **hihi subdomain** | https://hihi.omegamep.com |
| **Compose stack** | `OMEGAMEP` — auto-start ON |
| **Appdata (main)** | `/mnt/user/appdata/omegamep` — SQLite standalone |
| **Appdata (hihi)** | `/mnt/user/appdata/hihi-omegamep` — Postgres stack |
| **DB (main)** | SQLite (`db.sqlite3`) |
| **DB (hihi)** | Postgres 16, named volume `hihi-omegamep_pgdata` |
| **Status** | Main running (`omegamep-omegamep-1`); hihi stack stopped (Exited 255) |

---

### 7. Social Menace — `new.socialmenace.com`
Social platform. Django + SQLite.

| | |
|---|---|
| **Live URL** | https://new.socialmenace.com |
| **Compose stack** | `SOCIALMENACE` — auto-start OFF |
| **Local appdata** | `/mnt/user/appdata/socialmenace-live` |
| **DB** | SQLite (`db.sqlite3`) |
| **Status** | Running on Tokyo7 (`sm-web`) via traefik |

---

## Standalone Unraid Containers (non-compose)

These run as individual Unraid-managed containers, not compose stacks:

| Container | URL / Port | Notes |
|---|---|---|
| Plex | `tokyo7.local:32400` | Media server |
| Sonarr | `tokyo7.local:8989` | TV downloads |
| Radarr | `tokyo7.local:7878` | Movie downloads |
| Lidarr | `tokyo7.local:8686` | Music downloads |
| Prowlarr | `tokyo7.local:9696` | Indexer manager |
| NZBGet | `tokyo7.local:6789` | Usenet downloader |
| Tdarr | `tokyo7.local:8265` | Transcode automation |
| Audiobookshelf | `tokyo7.local:13378` | Audiobook server |
| Readarr | via binhex | Book downloads |
| Huntarr | `tokyo7.local` | Media hunt automation |
| Open-WebUI | `tokyo7.local:6969` | Ollama / ChatGPT UI |
| Ollama | `tokyo7.local:11434` | Local LLM runner |
| Syncthing | `tokyo7.local:8384` | File sync |
| Krusader | — | File manager GUI |
| Traefik | `:80/:443` | Reverse proxy for all compose stacks |

---

## Git SSH Aliases (in `~/.ssh/config`)
Multiple GitHub deploy keys are set up per project:

| Alias | Repo |
|---|---|
| `github-hihi-labs` | `hihilabs/hihi.labs` |
| `github-portfolio-blue` | `khildren/portfolio-blue` |
| `github-lostsignal` | `khildren/lostsignal` |
| `github.com` | `khildren/cp-worker`, `khildren/apothecary` |

---

## Quick Reference — get into anything

```bash
# Into Unraid (LAN)
ssh root@tokyo7.local

# Into VPS
ssh root@66.175.239.235

# Start a compose stack on Unraid
cd /boot/config/plugins/compose.manager/projects/HIHILABS
docker compose up -d

# Check all container status
docker ps -a --format "table {{.Names}}\t{{.Status}}"

# Tail logs for a container
docker logs -f hihilabs-hihilabs-1

# Get into hihilabs Django shell
docker exec -it hihilabs-hihilabs-1 python manage.py shell
```
