#!/usr/bin/env bash
# GPU referee — auto-bench the worker while games run, restore after.
# Runs every 30s via hihi-referee.timer. Manual 'hihi game' flag wins.
FLAG=/run/hihi-gamemode

# Detect Steam/Proton/gamescope games (covers native + Proton titles)
game_running() {
  pgrep -f 'steam_app_[0-9]+|gamescope|GameThread' >/dev/null 2>&1
}

unload_models() {
  ollama ps 2>/dev/null | awk 'NR>1{print $1}' | xargs -r -n1 ollama stop 2>/dev/null || true
}

if [ -f "$FLAG" ]; then
  exit 0  # manual game mode — referee stays out of it
fi

if game_running; then
  if systemctl is-active hihi-worker >/dev/null 2>&1; then
    systemctl stop hihi-worker
    unload_models
    logger -t hihi-referee "game detected — worker benched, VRAM freed"
  fi
else
  if ! systemctl is-active hihi-worker >/dev/null 2>&1; then
    systemctl start hihi-worker
    logger -t hihi-referee "game over — worker back on shift"
  fi
fi
