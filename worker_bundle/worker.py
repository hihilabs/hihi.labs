"""
HiHi Agent WorkerNode — generic pull-worker for hihilabs.xyz/workers
Polls the hub for queued jobs, dispatches to the appropriate handler,
ships results back, and reports progress/heartbeat.

Supported job types (JOB_HANDLERS):
  hvac_extract   — OCR + detect HVAC nameplates from CompanyCam photos
  library_sync   — bulk download all CC photos to local cache
  ai_task        — Loyd AI inference (cloud or local GPU)
"""
import os, sys, time, logging, requests, json, shutil
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ── Rich TUI setup ─────────────────────────────────────────────────────────────
from rich.console import Console
from rich.logging import RichHandler
from rich.live import Live
from rich.progress import (
    Progress, SpinnerColumn, BarColumn,
    MofNCompleteColumn, TextColumn, TimeElapsedColumn, TaskProgressColumn,
)
from rich.panel import Panel
from rich.table import Table
from rich import box as rbox

console = Console(highlight=False)

# Silence noisy HTTP / image-library loggers — only warnings bubble up
for _noisy in ("urllib3", "httpx", "httpcore", "requests", "PIL", "easyocr"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%H:%M:%S]",
    handlers=[RichHandler(
        console=console,
        rich_tracebacks=True,
        show_path=False,
        markup=True,
        log_time_format="[%H:%M:%S]",
    )],
)
log = logging.getLogger("worker")

# ── Config ─────────────────────────────────────────────────────────────────────
try:
    import psutil as _psutil
except ImportError:
    _psutil = None

load_dotenv()
load_dotenv("config.env", override=True)

PLESK_URL       = os.getenv("PLESK_URL",     "https://hihilabs.xyz/workers").rstrip("/")
WORKER_SECRET   = os.getenv("WORKER_SECRET", "")
WORKER_NAME     = os.getenv("WORKER_NAME",   "unraid")
POLL_INTERVAL   = int(os.getenv("POLL_INTERVAL", "10"))
JOBS_DIR        = Path(os.getenv("JOBS_DIR",        "jobs"))
PHOTO_CACHE_DIR = Path(os.getenv("PHOTO_CACHE_DIR", "photos"))
HIHI_URL        = ""  # optional secondary dashboard heartbeat
JOBS_DIR.mkdir(parents=True, exist_ok=True)
PHOTO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

VERSION = "2.3.1"
HEADERS = {"X-Worker-Key": WORKER_SECRET}

# ── Shared state ───────────────────────────────────────────────────────────────
_worker_busy     = 0
_current_job:    dict = {}
_last_error:     str  = ""
_pkg_status:     dict = {}
_last_heartbeat  = 0.0
_last_pkg_check  = 0.0
_jobs_completed  = 0
_jobs_failed     = 0
_session_start   = time.time()
_gpu_name        = ""   # detected once at startup, shown in Live panel + heartbeat

# ── API helpers ────────────────────────────────────────────────────────────────
def api(method, path, **kwargs):
    kwargs.setdefault("timeout", 20)
    r = getattr(requests, method)(f"{PLESK_URL}{path}", headers=HEADERS, **kwargs)
    r.raise_for_status()
    return r


def report_progress(job_id, **fields):
    try:
        api("post", f"/api/jobs/{job_id}/progress/", json=fields)
    except Exception as e:
        log.debug("progress report failed: %s", e)


# ── Display helpers ────────────────────────────────────────────────────────────
def _job_progress() -> Progress:
    return Progress(
        SpinnerColumn("dots2", style="cyan"),
        TextColumn("[bold cyan]{task.fields[phase]:<16}"),
        BarColumn(bar_width=None, style="dim cyan", complete_style="bright_cyan"),
        TaskProgressColumn(style="cyan"),
        MofNCompleteColumn(style="dim"),
        TextColumn("  [bold green]{task.fields[assets]}[/] assets"),
        TextColumn(" [blue]{task.fields[ocr]}[/] OCR"),
        TextColumn(" [yellow]{task.fields[skip]}[/] skip"),
        TimeElapsedColumn(),
        console=console,
        expand=True,
        transient=False,
    )


def _job_banner(job_id, job_type, label):
    console.rule(
        f"[bold cyan]▶  Job #{job_id}[/]  [dim]{job_type}[/]  [bold white]{label}[/]",
        style="cyan",
    )


def _job_done(job_id, elapsed_s, stats: dict):
    grid = Table.grid(padding=(0, 3))
    grid.add_column(style="dim")
    grid.add_column(style="bold bright_green")
    for k, v in stats.items():
        grid.add_row(k + ":", str(v))
    grid.add_row("elapsed:", str(timedelta(seconds=int(elapsed_s))))
    console.print(Panel(
        grid,
        title=f"[bold green]✓  Job #{job_id} complete[/]",
        border_style="green",
        expand=False,
        padding=(0, 2),
    ))


def _job_error(job_id, err):
    console.print(Panel(
        f"[red]{err}[/]",
        title=f"[bold red]✗  Job #{job_id} failed[/]",
        border_style="red",
        expand=False,
        padding=(0, 2),
    ))


# ── Job handler: hvac_extract ──────────────────────────────────────────────────
def handle_hvac_extract(job: dict):
    global _worker_busy, _current_job, _last_error, _jobs_completed, _jobs_failed
    job_id          = job["id"]
    project_id      = job["project_id"]
    project_name    = job.get("project_name", f"project {project_id}")
    tag_filter_json = job.get("tag_filter")
    brand_filter    = (job.get("brand_filter") or "").strip().lower() or None

    _worker_busy = 1
    _last_error  = ""
    _current_job = {"id": job_id, "type": "hvac_extract", "project": project_name,
                    "phase": "starting", "progress": 0}
    _job_banner(job_id, "hvac_extract", project_name)
    t0 = time.time()

    out_dir    = JOBS_DIR / str(job_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    tag_filter = set(json.loads(tag_filter_json)) if tag_filter_json else None

    try:
        _install_root = str(Path(__file__).resolve().parent)
        if _install_root not in sys.path:
            sys.path.insert(0, _install_root)

        from src.companycam_client import CompanyCam
        from src.detect            import propose_nameplate_crops
        from src.ocr               import ocr_text, remote_ocr_batch, _OCR_SERVER_URL
        from src.parse             import parse_fields
        from src.merge             import AssetStore
        from src.export            import export_csv_json, save_thumb
        from src.lifespan          import calculate_lifespan
        from src.serial_decoder    import decode_serial
        from src.cc_sync           import cached_photo_path
        from src.utils             import ensure_dir, sanitize_filename
        from PIL import Image

        raw_dir = ensure_dir(out_dir / "photos")

        _cc_token = os.getenv("COMPANYCAM_API_TOKEN", "")
        if _cc_token:
            cc = CompanyCam(token=_cc_token)
        else:
            cc = CompanyCam(
                base_url=f"{PLESK_URL}/api/cc",
                auth_headers={"X-Worker-Key": WORKER_SECRET},
            )

        try:
            proj  = cc._get(f"/projects/{project_id}").json()
            total = int(proj.get("photo_count") or proj.get("photos_count") or 0)
        except Exception:
            total = 0
        report_progress(job_id, total=total)

        api_tag_ids = None
        if tag_filter:
            tag_id_map  = cc.get_tag_id_map()
            api_tag_ids = [tag_id_map[n] for n in tag_filter if n in tag_id_map]

        assets     = AssetStore()
        downloaded = ocred = parsed_any = skipped = 0

        with _job_progress() as prog:
            task = prog.add_task("", total=total or 1,
                                 phase="↓ fetch", assets=0, ocr=0, skip=0)

            for i, photo in enumerate(cc.iter_project_photos(project_id, tag_ids=api_tag_ids)):
                pid = photo.get("id") or photo.get("uuid") or str(i)

                photo_tags = []
                if tag_filter:
                    photo_tags = cc.get_photo_tags(pid)
                    if not (tag_filter & {t.lower() for t in photo_tags}):
                        skipped += 1
                        prog.update(task, completed=i+1, skip=skipped)
                        report_progress(job_id, progress=i+1,
                                        downloaded=downloaded, skipped=skipped)
                        continue

                coords       = photo.get("coordinates") or {}
                gps_lat      = coords.get("lat")
                gps_lng      = coords.get("lng") or coords.get("lon")
                captured_at  = None
                captured_raw = photo.get("created_at") or photo.get("captured_at")
                if captured_raw:
                    try:
                        captured_at = datetime.utcfromtimestamp(
                            int(captured_raw)).strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        captured_at = str(captured_raw)
                caption = (photo.get("caption") or "").strip() or None

                fname = sanitize_filename(f"{pid}.jpg")
                dest  = str(raw_dir / fname)

                try:
                    cached = cached_photo_path(PHOTO_CACHE_DIR, project_id, str(pid))
                    if cached:
                        shutil.copy2(str(cached), dest)
                    else:
                        cc.download_photo(photo, dest)
                    webp_dest = dest.replace(".jpg", ".webp")
                    with Image.open(dest) as _raw:
                        _raw.convert("RGB").save(webp_dest, "WEBP", quality=85, method=4)
                    os.unlink(dest)
                    dest  = webp_dest
                    fname = fname.replace(".jpg", ".webp")
                    downloaded += 1
                except Exception as e:
                    skipped += 1
                    log.debug("skip download %s: %s", pid, e)
                    prog.update(task, completed=i+1, skip=skipped)
                    report_progress(job_id, progress=i+1,
                                    downloaded=downloaded, skipped=skipped)
                    continue

                try:
                    img = Image.open(dest)
                except Exception:
                    skipped += 1
                    prog.update(task, completed=i+1, skip=skipped)
                    continue

                prog.update(task, completed=i+1, phase="🔍 process",
                            assets=len(assets.by_key), ocr=ocred, skip=skipped)
                _current_job.update({"phase": "processing", "progress": i+1})

                props = propose_nameplate_crops(img, max_props=3) or [
                    {"bbox": (0, 0, img.width, img.height), "crop_img": img, "score": 0.2}
                ]

                if _OCR_SERVER_URL and len(props) > 1:
                    ocr_results = remote_ocr_batch([p["crop_img"] for p in props])
                else:
                    ocr_results = [ocr_text(p["crop_img"]) for p in props]

                best_record = best_bbox = None
                best_score  = -1.0

                for p, o in zip(props, ocr_results):
                    t = (o.get("text") or "").strip()
                    if t:
                        ocred += 1
                    rec    = parse_fields(t)
                    fscore = sum(rec.get("confidence", {}).values())
                    score  = float(o.get("mean_conf", 0)) + fscore + float(p.get("score", 0))
                    if score > best_score:
                        best_score, best_record, best_bbox = score, rec, p.get("bbox")

                if best_record:
                    best_record.update(calculate_lifespan(best_record))
                    decoded = decode_serial(
                        best_record.get("brand"), best_record.get("serial"))
                    if decoded.get("mfg_year"):
                        best_record.update({
                            "serial_mfg_year":  decoded["mfg_year"],
                            "serial_mfg_week":  decoded.get("mfg_week"),
                            "serial_mfg_conf":  round(decoded["confidence"], 2),
                            "serial_rule_used": decoded.get("rule_used"),
                        })
                        if not best_record.get("install_year") or decoded["confidence"] >= 0.8:
                            best_record["install_year"] = decoded["mfg_year"]
                            best_record.update(calculate_lifespan(best_record))

                any_field = best_record and any(
                    best_record.get(k)
                    for k in ("model", "serial", "brand", "refrigerant", "tonnage")
                )
                if any_field:
                    parsed_any += 1

                if brand_filter and best_record:
                    if brand_filter not in (best_record.get("brand") or "").lower():
                        best_record = None
                        skipped += 1

                if best_record:
                    if not tag_filter and not photo_tags:
                        photo_tags = cc.get_photo_tags(pid)
                    for k, v in [("location_tags", "; ".join(photo_tags) if photo_tags else None),
                                  ("captured_at", captured_at), ("gps_lat", gps_lat),
                                  ("gps_lng", gps_lng),          ("caption", caption)]:
                        if v is not None:
                            best_record[k] = v
                    if any_field:
                        cc.write_photo_description(pid, best_record)
                    try:
                        thumb = save_thumb(dest, best_bbox, out_dir) if best_bbox else dest
                    except Exception:
                        thumb = dest
                    best_record.setdefault("images", []).append(
                        {"file": fname, "crop": thumb})
                    assets.upsert(best_record, origin={
                        "photo_id": pid, "file": fname,
                        "tags": photo_tags, "gps_lat": gps_lat, "gps_lng": gps_lng,
                    })

                prog.update(task, completed=i+1, phase="🔍 process",
                            assets=len(assets.by_key), ocr=ocred, skip=skipped)

                if (i + 1) % 5 == 0 or (i + 1) == total:
                    report_progress(job_id, progress=i+1, downloaded=downloaded,
                                    ocred=ocred, parsed=parsed_any,
                                    skipped=skipped, assets=len(assets.by_key))

            prog.update(task, completed=total or downloaded, phase="📦 export",
                        assets=len(assets.by_key), ocr=ocred, skip=skipped)

        # ── Export & ship ──────────────────────────────────────────────────────
        checklists = cc.get_project_checklists(project_id)
        if checklists:
            (out_dir / "checklists.json").write_text(json.dumps(checklists, indent=2))

        _current_job["phase"] = "exporting"
        export_csv_json(assets.to_list(), out_dir)

        files = {}
        data  = {"assets": len(assets.by_key), "downloaded": downloaded, "total": total}
        for fmt in ("csv", "json", "xlsx"):
            p = out_dir / f"hvac_assets.{fmt}"
            if p.exists():
                files[fmt] = open(p, "rb")
        api("post", f"/api/jobs/{job_id}/complete/", files=files, data=data)
        for f in files.values():
            f.close()

        _jobs_completed += 1
        _job_done(job_id, time.time() - t0, {
            "assets":  len(assets.by_key),
            "photos":  downloaded,
            "OCR":     ocred,
            "skipped": skipped,
        })

    except Exception as e:
        _jobs_failed += 1
        _last_error = str(e)[:300]
        _job_error(job_id, e)
        log.exception("Job #%s traceback", job_id)
        try:
            api("post", f"/api/jobs/{job_id}/error/", json={"error": str(e)[:500]})
        except Exception:
            pass
    finally:
        _worker_busy = 0
        _current_job = {}


# ── Job handler: library_sync ──────────────────────────────────────────────────
def handle_library_sync(job: dict):
    global _worker_busy, _current_job, _last_error, _jobs_completed, _jobs_failed
    sync_id = job["id"]
    _worker_busy = 1
    _last_error  = ""
    _current_job = {"id": sync_id, "type": "library_sync", "phase": "starting"}
    _job_banner(sync_id, "library_sync", str(PHOTO_CACHE_DIR))
    t0 = time.time()

    try:
        _install_root = str(Path(__file__).resolve().parent)
        if _install_root not in sys.path:
            sys.path.insert(0, _install_root)
        from src.companycam_client import CompanyCam
        from src.cc_sync           import sync_library

        _cc_token = os.getenv("COMPANYCAM_API_TOKEN", "")
        cc = CompanyCam(token=_cc_token) if _cc_token else CompanyCam()
        synced = [0]

        with _job_progress() as prog:
            task = prog.add_task("", total=None,
                                 phase="↓ sync", assets=0, ocr=0, skip=0)

            def _cb(stats):
                n = stats.get("synced", 0)
                synced[0] = n
                prog.update(task, completed=n, assets=n,
                             phase="↓ sync" if not stats.get("done") else "✓ done")
                report_progress(sync_id, **stats)

            sync_library(PHOTO_CACHE_DIR, cc, progress_cb=_cb)
            prog.update(task, completed=synced[0], phase="✓ done")

        api("post", f"/api/jobs/{sync_id}/complete/",
            json={"synced": synced[0], "elapsed_s": round(time.time() - t0, 2)})
        _jobs_completed += 1
        _job_done(sync_id, time.time() - t0, {"synced photos": synced[0]})

    except Exception as e:
        _jobs_failed += 1
        _last_error = str(e)[:300]
        _job_error(sync_id, e)
        log.exception("Sync #%s traceback", sync_id)
        try:
            api("post", f"/api/jobs/{sync_id}/error/", json={"error": str(e)[:500]})
        except Exception:
            pass
    finally:
        _worker_busy = 0
        _current_job = {}


# ── Loyd — internal AI utility ────────────────────────────────────────────────
# Loyd routes tasks to the best available backend automatically:
#   small/structured → Claude API (fast, accurate)
#   large context / no key → Ollama local GPU (free, no size limit)
_LOYD_CHAR_LIMIT  = 180_000   # ~40k tokens — route above this to local GPU
_OLLAMA_URL       = os.getenv("OLLAMA_URL",         "http://10.0.0.157:11434")
_LOYD_LOCAL_MODEL = os.getenv("OLLAMA_AI_MODEL",    "llama3.1:8b")
_ANTHROPIC_KEY    = os.getenv("ANTHROPIC_API_KEY",  "")
_LOYD_CLOUD_MODEL = os.getenv("ANTHROPIC_AI_MODEL", "claude-haiku-4-5-20251001")


def loyd(prompt: str, context: str = "", system: str = "",
         force: str = "auto", max_tokens: int = 2048) -> dict:
    """
    Loyd — internal AI. Auto-routes to best backend.
    force: 'auto' | 'cloud' | 'local'
    Returns: {text, backend, model, tokens_in, tokens_out}
    """
    total_chars = len(system) + len(prompt) + len(context)
    use_local = (
        force == "local"
        or (force == "auto" and (not _ANTHROPIC_KEY or total_chars > _LOYD_CHAR_LIMIT))
    )

    if not use_local:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=_ANTHROPIC_KEY)
            resp = client.messages.create(
                model=_LOYD_CLOUD_MODEL,
                max_tokens=max_tokens,
                system=system or "You are Loyd, a precise internal technical assistant. Be concise.",
                messages=[{"role": "user", "content": f"{prompt}\n\n{context}".strip()}],
            )
            return {
                "text":       resp.content[0].text,
                "backend":    "cloud",
                "model":      _LOYD_CLOUD_MODEL,
                "tokens_in":  resp.usage.input_tokens,
                "tokens_out": resp.usage.output_tokens,
            }
        except Exception as e:
            log.warning("Loyd cloud failed, routing to local GPU: %s", e)

    # Local GPU via Ollama — no size limit, no cost
    r = requests.post(f"{_OLLAMA_URL}/api/generate", timeout=300, json={
        "model":   _LOYD_LOCAL_MODEL,
        "prompt":  f"{system}\n\n{prompt}\n\n{context}".strip(),
        "stream":  False,
        "options": {"num_predict": max_tokens},
    })
    r.raise_for_status()
    data = r.json()
    return {
        "text":       data.get("response", ""),
        "backend":    "local",
        "model":      _LOYD_LOCAL_MODEL,
        "tokens_in":  data.get("prompt_eval_count", 0),
        "tokens_out": data.get("eval_count", 0),
    }


def handle_ai_task(job: dict):
    """
    Generic AI inference job.
    Payload: {prompt, context?, system?, model?, max_tokens?, tags?}
    tags examples: ['security', 'error_log', 'code_review', 'summarize']
    """
    global _worker_busy, _current_job, _last_error, _jobs_completed, _jobs_failed
    job_id  = job["id"]
    payload = job.get("payload") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {"prompt": payload}

    prompt     = payload.get("prompt", "")
    context    = payload.get("context", "")
    system     = payload.get("system", "You are a precise technical assistant. Be concise.")
    force      = payload.get("model", "auto")   # 'auto' | 'cloud' | 'local'
    max_tokens = int(payload.get("max_tokens", 2048))
    tags       = payload.get("tags", [])

    if not prompt:
        try:
            api("post", f"/api/jobs/{job_id}/error/", json={"error": "no prompt in payload"})
        except Exception:
            pass
        return

    _worker_busy = 1
    _last_error  = ""
    _current_job.update({"id": job_id, "type": "ai_task", "phase": "thinking"})
    t0 = time.time()

    log.info("Loyd task [bold cyan]#%s[/] [dim]%s[/]  ctx=%d chars  tags=%s",
             job_id, force, len(context), tags or "none")

    with _job_progress() as prog:
        task = prog.add_task("", phase="routing", total=3, assets="-", ocr="-", skip="-")
        try:
            prog.update(task, phase="loyd →", completed=1)

            result = loyd(prompt, context, system, force, max_tokens)

            prog.update(task, phase="posting", completed=2)
            elapsed = time.time() - t0

            api("post", f"/api/jobs/{job_id}/complete/", json={
                "text":       result["text"],
                "backend":    result["backend"],
                "model":      result["model"],
                "tokens_in":  result["tokens_in"],
                "tokens_out": result["tokens_out"],
                "elapsed_s":  round(elapsed, 2),
                "tags":       tags,
            })
            prog.update(task, phase="done", completed=3)
            _jobs_completed += 1
            _job_done(job_id, elapsed, {
                "backend": result["backend"],
                "tokens":  result["tokens_out"],
            })

        except Exception as e:
            _jobs_failed += 1
            _last_error = str(e)[:300]
            _job_error(job_id, e)
            log.exception("AI task #%s failed", job_id)
            try:
                api("post", f"/api/jobs/{job_id}/error/", json={"error": str(e)[:500]})
            except Exception:
                pass
        finally:
            _worker_busy = 0
            _current_job.clear()


# ── Job dispatcher ─────────────────────────────────────────────────────────────
JOB_HANDLERS = {
    "hvac_extract": handle_hvac_extract,
    "library_sync": handle_library_sync,
    "ai_task":      handle_ai_task,
    # Future: "security_scan", "log_analysis", "code_review", "report_gen"
}


# ── Heartbeat ──────────────────────────────────────────────────────────────────
def _detect_gpu() -> str:
    try:
        import subprocess
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        names = [n.strip() for n in r.stdout.strip().splitlines() if n.strip()]
        return names[0] if names else ""
    except Exception:
        return ""


def _detect_vram() -> tuple:
    """Returns (used_mb, total_mb) or (None, None)."""
    try:
        import subprocess
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        parts = r.stdout.strip().split(",")
        if len(parts) == 2:
            return int(parts[0].strip()), int(parts[1].strip())
    except Exception:
        pass
    return None, None


def _probe_packages():
    global _pkg_status
    for pkg, imp in [("httpx","httpx"), ("anthropic","anthropic"),
                     ("rapidfuzz","rapidfuzz"), ("easyocr","easyocr")]:
        try:
            __import__(imp); _pkg_status[pkg] = True
        except ImportError:
            _pkg_status[pkg] = False


def send_heartbeat():
    global _last_heartbeat, _last_pkg_check
    now = time.time()
    if now - _last_heartbeat < 30:
        return
    if now - _last_pkg_check > 300:
        _probe_packages()
        _last_pkg_check = now
    payload = {
        "name":        WORKER_NAME,
        "version":     VERSION,
        "gpu":         _gpu_name,
        "active_jobs": _worker_busy,
        "current_job": _current_job or None,
        "last_error":  _last_error or None,
    }
    if _psutil:
        mem = _psutil.virtual_memory()
        payload.update({
            "cpu_pct":      _psutil.cpu_percent(interval=0.2),
            "mem_pct":      mem.percent,
            "mem_used_gb":  round(mem.used / 1e9, 1),
            "mem_total_gb": round(mem.total / 1e9, 1),
        })
    if _gpu_name:
        vused, vtotal = _detect_vram()
        if vtotal:
            payload.update({"vram_used": vused, "vram_total": vtotal})
    try:
        r = api("post", "/api/heartbeat/", json=payload)
        _last_heartbeat = now
        cmd = r.json().get("command")
        if cmd:
            _exec_command(cmd)
    except Exception as e:
        log.debug("heartbeat failed: %s", e)

    if HIHI_URL:
        try:
            requests.post(
                f"{HIHI_URL}/api/heartbeat/",
                json={**payload, "worker_type": "pull"},
                headers={"X-Worker-Key": WORKER_SECRET},
                timeout=5,
            )
        except Exception:
            pass


def _exec_command(cmd: str):
    if _worker_busy:
        log.info("Deferring command [bold]%s[/] — job in progress", cmd)
        return
    log.info("Command: [bold cyan]%s[/]", cmd)
    if cmd == "restart":
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
        os._exit(0)
    elif cmd == "update_restart":
        _download_and_restart()
    else:
        log.warning("Unknown command: %s", cmd)


def _download_and_restart():
    import zipfile, tempfile, subprocess
    try:
        log.info("Downloading update bundle…")
        # Auth via X-Worker-Key header — never leak secrets in URL params
        r = requests.get(
            f"{PLESK_URL}/download/",
            headers=HEADERS,
            timeout=60,
            stream=True,
        )
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as fh:
            for chunk in r.iter_content(8192):
                fh.write(chunk)
            tmp = fh.name

        # Zip-slip protection: reject any entry that would escape the target dir
        target = Path(__file__).resolve().parent
        with zipfile.ZipFile(tmp, "r") as z:
            for member in z.namelist():
                dest = (target / member).resolve()
                if not str(dest).startswith(str(target)):
                    log.warning("Blocked unsafe zip entry: %s", member)
                    continue
                z.extract(member, target)

        Path(tmp).unlink(missing_ok=True)
        subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "httpx", "anthropic", "requests", "python-dotenv",
             "Pillow", "pandas", "xlsxwriter", "psutil", "rapidfuzz",
             "numpy", "opencv-python-headless", "easyocr", "rich", "--quiet"],
            check=False,
        )
        log.info("Bundle applied — restarting")
        subprocess.Popen([sys.executable] + sys.argv)
        os._exit(0)
    except Exception as e:
        log.error("Self-update failed: %s", e)


def _bootstrap_packages():
    _probe_packages()
    missing = [p for p, ok in _pkg_status.items() if not ok]
    if not missing:
        return
    log.info("Installing: %s", ", ".join(missing))
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install"] + missing + ["--quiet"],
                   check=False)
    log.info("Packages installed — restarting")
    subprocess.Popen([sys.executable] + sys.argv)
    sys.exit(0)


# ── Startup banner ─────────────────────────────────────────────────────────────
def _print_banner(gpu: str):
    rows = [
        f"[dim]hub[/]      [cyan]{PLESK_URL}[/]",
        f"[dim]worker[/]   [white]{WORKER_NAME}[/]  [dim]v{VERSION}[/]",
        f"[dim]poll[/]     every [white]{POLL_INTERVAL}s[/]",
        f"[dim]handles[/]  " + "  ".join(f"[cyan]{k}[/]" for k in JOB_HANDLERS),
    ]
    if gpu:
        rows.append(f"[dim]GPU[/]      [green]{gpu}[/]")
    console.print(Panel(
        "\n".join(rows),
        title="[bold cyan]HiHi Agent[/]",
        border_style="cyan",
        expand=False,
        padding=(0, 2),
    ))


# ── Live status panel ──────────────────────────────────────────────────────────
def _status_panel() -> Panel:
    uptime = timedelta(seconds=int(time.time() - _session_start))
    t = Table(box=None, show_header=False, padding=(0, 1), expand=False)
    t.add_column(style="dim",   no_wrap=True)
    t.add_column(no_wrap=True)
    t.add_row("hub",    f"[cyan]{PLESK_URL}[/]")
    t.add_row("worker", f"[white]{WORKER_NAME}[/]  [dim]v{VERSION}[/]")
    if _gpu_name:
        t.add_row("GPU",    f"[green]{_gpu_name}[/]")
    t.add_row("uptime", f"[white]{uptime}[/]")
    t.add_row("status", "[yellow]busy[/]" if _worker_busy else "[dim]idle[/]")
    t.add_row("done",   f"[bold green]{_jobs_completed}[/]")
    t.add_row("failed", f"[bold red]{_jobs_failed}[/]" if _jobs_failed else "[dim]0[/]")
    if _current_job:
        t.add_row("job", f"[cyan]#{_current_job.get('id','')}[/] [dim]{_current_job.get('phase','')}[/]")
    return Panel(t, title="[bold cyan]HiHi Agent[/]", border_style="cyan",
                 expand=False, padding=(0, 1))


# ── Main loop ──────────────────────────────────────────────────────────────────
def main():
    global _gpu_name
    _bootstrap_packages()
    _gpu_name = _detect_gpu()
    _print_banner(_gpu_name)

    with Live(_status_panel(), console=console, refresh_per_second=0.5,
              vertical_overflow="visible") as live:
        while True:
            live.update(_status_panel())
            send_heartbeat()
            try:
                # Regular job queue
                jobs = api("get", "/api/jobs/pending/").json().get("jobs", [])
                for job in jobs:
                    job_id   = job["id"]
                    job_type = job.get("type", "hvac_extract")
                    handler  = JOB_HANDLERS.get(job_type)
                    if not handler:
                        log.warning("Unknown job type [bold]%s[/] — skipping #%s", job_type, job_id)
                        continue
                    try:
                        api("post", f"/api/jobs/{job_id}/claim/", json={"worker": WORKER_NAME})
                        log.info("Claimed [bold cyan]#%s[/] [dim](%s)[/]  %s",
                                 job_id, job_type, job.get("label", ""))
                        handler(job)
                        break
                    except requests.HTTPError as e:
                        if e.response.status_code == 409:
                            continue
                        log.warning("Claim error #%s: %s", job_id, e)

            except Exception as e:
                log.warning("Poll error: %s", e)

            live.update(_status_panel())
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
