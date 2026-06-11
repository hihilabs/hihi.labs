# HiHi Labs — Dev & Deploy Workflow

## Live app
- URL: https://hihilabs.xyz
- VPS: 66.175.239.235 (root)
- App root: /var/www/vhosts/communityplaylist.com/tokyo7.communityplaylist.com/
- Venv: venv/
- DB: db.sqlite3 (SQLite, in app root)
- Static: static/css/main.css (served by WhiteNoise)

---

## SSH paths

### At home (local network)
```
# Step 1 — into Unraid (Tokyo7)
ssh -i ~/.ssh/id_ed25519_unraid root@tokyo7.local   # LAN
# or: root@192.168.0.28

# Step 2 — from Unraid into VPS
ssh -i /root/.ssh/id_ed25519_unraid root@66.175.239.235

# Then cd into app
cd /var/www/vhosts/communityplaylist.com/tokyo7.communityplaylist.com
source venv/bin/activate
```

### On the road (external network)
```
# Direct to VPS — no Unraid hop needed, VPS is public
ssh -i ~/.ssh/id_ed25519_unraid root@66.175.239.235

cd /var/www/vhosts/communityplaylist.com/tokyo7.communityplaylist.com
source venv/bin/activate
```

> NOTE: Unraid (Tokyo7 — tokyo7.local / 192.168.0.28) is LAN-only. From the road, skip it entirely.
> Edit directly on the VPS and commit from there.

---

## Making changes

### Edit a template
```bash
nano templates/projects/detail.html
# or
nano templates/base.html
```
Templates reload immediately — no server restart needed.

### Edit Python (models/views/urls)
```bash
nano apps/projects/views.py
# then reload gunicorn:
kill -HUP $(pgrep -f 'gunicorn.*tokyo7' | head -1)
```

### Edit CSS
```bash
nano static/css/main.css
# IMPORTANT: Always run deploy.sh after CSS changes!
./deploy.sh
```
WhiteNoise serves from staticfiles/ (STATIC_ROOT), not static/.
 copies files across, and the CSS URL auto-versions from git hash.

### OLD — do not use

```bash
nano static/css/main.css
# No restart needed — WhiteNoise serves it directly.
# Users on service worker may need Ctrl+Shift+R (hard refresh).
```

### Run management commands
```bash
source venv/bin/activate
python manage.py migrate
python manage.py shell
python manage.py check
```

---

## Commit & push
```bash
git add -A
git commit -m "your message"
git push origin master
```

---

## Gunicorn reload (after Python changes)
```bash
kill -HUP $(pgrep -f 'gunicorn.*tokyo7' | head -1)
# Verify workers are up:
pgrep -f 'gunicorn.*tokyo7' | wc -l
```

---

## Key app paths
| App | Path |
|-----|------|
| CSS | static/css/main.css |
| Base template | templates/base.html |
| Dashboard | templates/dashboard.html |
| Projects | apps/projects/ · templates/projects/ |
| Clients | apps/clients/ · templates/clients/ |
| Proposals | apps/proposals/ · templates/proposals/ |
| Contracts | apps/contracts/ · templates/contracts/ |
| Services | apps/services/ · templates/services/ |
| Sound | apps/sound/ · templates/sound/ |
| Chat/AI | apps/claude_ai/ · templates/claude_ai/ |
| Settings | hihilabs/settings.py |
| URLs | hihilabs/urls.py |
| Core views | hihilabs/views.py |

---

## Service worker cache note
CSS and JS are cached by the PWA service worker (sw.js, key: hl-v1).
If a CSS change isn't showing for a user, they need Ctrl+Shift+R.
To force all users to re-fetch, bump CACHE_VER in static/sw.js.
