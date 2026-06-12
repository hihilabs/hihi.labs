#!/usr/bin/env bash
# One-shot install: worker service + GPU referee + hihi switch (run with sudo)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
WORKER_DIR="$(dirname "$DIR")"
RUN_USER="${SUDO_USER:-binsky}"

install -m 755 "$DIR/hihi" /usr/local/bin/hihi
install -m 755 "$DIR/hihi-referee.sh" /usr/local/bin/hihi-referee.sh

cat > /etc/systemd/system/hihi-worker.service <<EOF
[Unit]
Description=HiHi Labs pull worker (BinskyBox)
After=network-online.target ollama.service
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$WORKER_DIR
ExecStart=$WORKER_DIR/venv/bin/python $WORKER_DIR/worker.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/hihi-referee.service <<EOF
[Unit]
Description=HiHi GPU referee (bench worker while gaming)

[Service]
Type=oneshot
ExecStart=/usr/local/bin/hihi-referee.sh
EOF

cat > /etc/systemd/system/hihi-referee.timer <<EOF
[Unit]
Description=Run GPU referee every 30s

[Timer]
OnBootSec=60
OnUnitActiveSec=30

[Install]
WantedBy=timers.target
EOF

# let the hihi switch work without password prompts for these exact actions
cat > /etc/sudoers.d/hihi-switch <<EOF
$RUN_USER ALL=(root) NOPASSWD: /usr/bin/systemctl start hihi-worker, /usr/bin/systemctl stop hihi-worker, /usr/bin/touch /run/hihi-gamemode, /usr/bin/rm -f /run/hihi-gamemode
EOF
chmod 440 /etc/sudoers.d/hihi-switch

systemctl daemon-reload
systemctl enable --now hihi-worker.service hihi-referee.timer
echo "installed. try: hihi status"
