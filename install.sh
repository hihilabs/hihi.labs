#!/usr/bin/env bash
# Rise Audio Recording Addon — install / re-install after RiseCRM upgrades
# Run from: the root of your RiseCRM installation
#   bash /path/to/rise-audio-recording/install.sh
# or with RISE_ROOT set:
#   RISE_ROOT=/var/www/... bash install.sh
# Requires HTTPS — the mic button is disabled on plain HTTP by browsers.
set -e

ADDON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RISE_ROOT="${RISE_ROOT:-$(pwd)}"

echo "◉ Rise Audio Recording Addon — install"
echo "  addon dir : $ADDON_DIR"
echo "  rise root : $RISE_ROOT"
echo ""

# ── 1. Check rise root
if [ ! -f "$RISE_ROOT/app/Controllers/Tasks.php" ]; then
    echo "ERROR: $RISE_ROOT does not look like a RiseCRM root (Tasks.php not found)"
    exit 1
fi

# ── 2. Patch core files
echo "[1/2] Patching core files..."
RISE_ROOT="$RISE_ROOT" python3 "$ADDON_DIR/patches/patch_timeline_preview.py"
RISE_ROOT="$RISE_ROOT" python3 "$ADDON_DIR/patches/patch_notes_view.py"
RISE_ROOT="$RISE_ROOT" python3 "$ADDON_DIR/patches/patch_todo_view.py"
echo "  ✓ view files patched"

# ── 3. SQL migration
echo "[2/2] Running SQL migration..."
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASS" ] || [ -z "$DB_NAME" ]; then
    echo "  SKIP — set DB_HOST, DB_USER, DB_PASS, DB_NAME env vars to auto-migrate"
    echo "  Or run manually: mysql -u USER -pPASS DBNAME < $ADDON_DIR/sql/up.sql"
else
    mysql -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$ADDON_DIR/sql/up.sql"
    echo "  ✓ SQL migration applied (enable_audio_recording = 1)"
fi

echo ""
echo "◉ Install complete."
echo "  → Requires HTTPS — mic button auto-disables on plain HTTP."
echo "  → In any task, note, or todo: click the mic icon next to the attachment button."
echo "  → Recordings appear as inline audio players above other attachments."
echo "  → Recordings are named recording-{duration}{ms}.webm and stored in timeline_files/."
