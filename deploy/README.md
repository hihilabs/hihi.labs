# Deploy artifacts — HiHi Labs

## Realtime websockets (whiteboard rooms / Channels)
HTTP is served by gunicorn (WSGI) via Apache as normal. Websockets are served
separately so the HTTP path is never at risk:

- **`hihilabs-asgi.service`** → uvicorn runs `hihilabs.asgi:application` on
  `127.0.0.1:8001`. Install to `/etc/systemd/system/`, `systemctl enable --now`.
- **`nginx-ws-location.conf`** → the `/ws/` location that proxies to uvicorn with
  upgrade headers, bypassing Apache. Install to
  `/var/www/vhosts/system/hihilabs.xyz/conf/vhost_nginx.conf`, then
  `plesk sbin httpdmng --reconfigure-domain hihilabs.xyz`.
- **Channel layer** = Redis db 5 (`REDIS_CHANNEL_URL` env override), see settings.py.
- Deps: `pip install "uvicorn[standard]" channels_redis channels`.
