#!/usr/bin/env bash
# Django HiHi Footer — install
# Copies base_site.html into your Django project's templates/admin/ directory.
# Usage: TEMPLATES_DIR=/path/to/your/templates bash install.sh
set -e

ADDON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${TEMPLATES_DIR:-./templates}/admin"

mkdir -p "$DEST"

if [ -f "$DEST/base_site.html" ]; then
    echo "Existing base_site.html found — backing up to base_site.html.bak"
    cp "$DEST/base_site.html" "$DEST/base_site.html.bak"
fi

cp "$ADDON_DIR/templates/admin/base_site.html" "$DEST/base_site.html"
echo "◉ HiHi footer installed at $DEST/base_site.html"
echo "  Restart your Django dev server or gunicorn to see the change."
