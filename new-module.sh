#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# new-module.sh — scaffold a new hihilabs module
#
# Usage:
#   ./new-module.sh <slug> <"Display Name"> <type>
#
# Example:
#   ./new-module.sh ip-scanner "IP Scanner" utility
#
# What it does:
#   1. Creates /mnt/user/appdata/<slug>-hihilabs/ with nginx docker-compose
#   2. Creates a starter landing page at www/index.html
#   3. Adds <slug>.hihilabs.xyz DNS A record via Cloudflare
#   4. Starts the container (Traefik routes it automatically)
#   5. Prints the registry snippet to paste into apps/modules/registry.py
# ─────────────────────────────────────────────────────────────────────────────

set -e

SLUG="${1}"
NAME="${2}"
TYPE="${3:-utility}"

if [[ -z "$SLUG" || -z "$NAME" ]]; then
  echo "Usage: ./new-module.sh <slug> \"Display Name\" [type]"
  echo "Types: utility | data | ai | infra"
  exit 1
fi

CF_TOKEN="${CF_TOKEN:?CF_TOKEN env var required}"
ZONE_ID="${CF_ZONE_ID:?CF_ZONE_ID env var required}"
ORIGIN_IP="${ORIGIN_IP:?ORIGIN_IP env var required}"
APPDATA="/mnt/user/appdata/${SLUG}-hihilabs"

echo ""
echo "▶ Creating module: ${NAME} (${SLUG}.hihilabs.xyz)"
echo ""

# ── 1. Directory + docker-compose ────────────────────────────────────────────
mkdir -p "${APPDATA}/www"

cat > "${APPDATA}/docker-compose.yml" << EOF
services:
  ${SLUG}-hihilabs:
    image: nginx:alpine
    restart: unless-stopped
    volumes:
      - ./www:/usr/share/nginx/html:ro
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.${SLUG}-hihilabs.rule=Host(\`${SLUG}.hihilabs.xyz\`)"
      - "traefik.http.routers.${SLUG}-hihilabs.entrypoints=websecure"
      - "traefik.http.routers.${SLUG}-hihilabs.tls=true"
      - "traefik.http.routers.${SLUG}-hihilabs.tls.certresolver=letsencrypt"
      - "traefik.http.services.${SLUG}-hihilabs.loadbalancer.server.port=80"
    networks:
      - traefik

networks:
  traefik:
    external: true
EOF

# ── 2. Starter landing page ───────────────────────────────────────────────────
cat > "${APPDATA}/www/index.html" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${NAME} — hihilabs</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&display=swap" rel="stylesheet">
  <style>
    :root { --bg:#0a0a0f; --surface:#111118; --border:#1e1e2e; --accent:#7c6af7; --accent2:#4fffb0; --text:#e8e8f0; --muted:#5a5a72; --mono:'DM Mono',monospace; --sans:'Syne',sans-serif; }
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
    body{background:var(--bg);color:var(--text);font-family:var(--mono);min-height:100vh;padding:48px 24px;}
    .page{max-width:720px;margin:0 auto;}
    .topbar{display:flex;justify-content:space-between;align-items:center;padding-bottom:32px;border-bottom:1px solid var(--border);margin-bottom:48px;}
    .brand{font-family:var(--sans);font-weight:800;font-size:13px;letter-spacing:.08em;}
    .brand span{color:var(--accent);}
    .tag{font-size:10px;color:var(--muted);letter-spacing:.15em;}
    .label{font-size:10px;letter-spacing:.2em;color:var(--accent2);margin-bottom:14px;}
    h1{font-family:var(--sans);font-weight:800;font-size:clamp(28px,6vw,48px);line-height:1.1;margin-bottom:20px;}
    h1 em{color:var(--accent);font-style:normal;}
    p{font-size:13px;color:var(--muted);line-height:1.8;max-width:560px;}
    .footer{margin-top:80px;padding-top:24px;border-top:1px solid var(--border);font-size:10px;color:var(--muted);}
  </style>
</head>
<body>
<div class="page">
  <div class="topbar">
    <div class="brand"><span>hihi</span>labs / ${SLUG}</div>
    <div class="tag">${TYPE^^} MODULE</div>
  </div>
  <div class="label">// ${SLUG} v0.1</div>
  <h1>${NAME}<br><em>coming soon.</em></h1>
  <p>This module is under construction. Check back soon.</p>
  <div class="footer">hihilabs.xyz &nbsp;·&nbsp; ${SLUG}.hihilabs.xyz</div>
</div>
</body>
</html>
EOF

# ── 3. DNS record ─────────────────────────────────────────────────────────────
echo "  → Adding DNS: ${SLUG}.hihilabs.xyz → ${ORIGIN_IP}"
DNS_RESULT=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records" \
  -H "Authorization: Bearer ${CF_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "{\"type\":\"A\",\"name\":\"${SLUG}\",\"content\":\"${ORIGIN_IP}\",\"ttl\":1,\"proxied\":true}")

if echo "$DNS_RESULT" | grep -q '"success":true'; then
  echo "  ✓ DNS record created"
else
  echo "  ✗ DNS error (may already exist): $(echo $DNS_RESULT | python3 -c 'import sys,json; print(json.load(sys.stdin).get("errors","?"))')"
fi

# ── 4. Start container ────────────────────────────────────────────────────────
echo "  → Starting container..."
cd "${APPDATA}" && docker compose up -d 2>&1 | grep -E "Started|Created|Pulling|error" || true
echo "  ✓ Container up"

# ── 5. Registry snippet ───────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Paste this into /mnt/user/appdata/hihilabs/apps/modules/registry.py:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat << EOF

    {
        'slug':        '${SLUG}',
        'name':        '${NAME}',
        'type':        '${TYPE}',
        'icon':        'fa-bolt',
        'color':       '#7c6af7',
        'description': 'TODO — one sentence description.',
        'status':      'wip',
        'platform':    'Web',
        'live_url':    'https://${SLUG}.hihilabs.xyz',
        'source_url':  '',
        'tags':        [],
    },
EOF
echo ""
echo "  Then update the icon, color, description, and status."
echo ""
echo "  Live at: https://${SLUG}.hihilabs.xyz  (cert provisions in ~60s)"
echo "  Files:   ${APPDATA}/www/index.html"
echo ""
