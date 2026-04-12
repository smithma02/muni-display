#!/bin/bash
# deploy.sh — Copy project files to a Raspberry Pi and install the systemd service.
#
# Usage:
#   ./deploy.sh <pi-host>
#   ./deploy.sh pi@192.168.1.42
#   ./deploy.sh transit.local
#
# The script will:
#   1. Copy all project files to ~/muni-display on the Pi
#   2. Install and enable the systemd service
#   3. Prompt you to restart the service if it was already running

set -e

# ── Args ──────────────────────────────────────────────────────────────────────
if [ -z "$1" ]; then
    echo "Usage: $0 <pi-host>"
    echo "  e.g. $0 pi@192.168.1.42"
    echo "       $0 transit.local"
    exit 1
fi

HOST="$1"
# Ensure host has a user prefix; default to 'pi' if not provided
if [[ "$HOST" != *"@"* ]]; then
    HOST="pi@${HOST}"
fi

REMOTE_DIR="/home/pi/muni-display"

echo "▶ Deploying to ${HOST}:${REMOTE_DIR}"

# ── Files to copy ─────────────────────────────────────────────────────────────
FILES=(
    main.py
    muni.py
    server.py
    utils.py
    einkUtils.py
    maintenance.py
    hello.html
    web.html
    requirements.txt
    startup.sh
    sample.config.yaml
    config.muni.yaml
    config.bart.yaml
)

# ── Create remote directory structure ─────────────────────────────────────────
echo "▶ Creating remote directories..."
ssh "$HOST" "mkdir -p ${REMOTE_DIR}/images"

# ── Copy Python files and templates ───────────────────────────────────────────
echo "▶ Copying project files..."
scp "${FILES[@]}" "${HOST}:${REMOTE_DIR}/"

# ── Copy images folder ────────────────────────────────────────────────────────
echo "▶ Copying images..."
scp images/* "${HOST}:${REMOTE_DIR}/images/"

# ── Copy config only if one doesn't already exist on the Pi ───────────────────
echo "▶ Checking config..."
if ssh "$HOST" "[ ! -f ${REMOTE_DIR}/config.yaml ]"; then
    echo "  No config.yaml found on Pi — copying sample.config.yaml as config.yaml"
    ssh "$HOST" "cp ${REMOTE_DIR}/sample.config.yaml ${REMOTE_DIR}/config.yaml"
    echo "  ⚠️  Edit ${REMOTE_DIR}/config.yaml on the Pi and add your 511.org API key before starting."
else
    echo "  config.yaml already exists on Pi — skipping (your settings are preserved)"
fi

# ── Ensure startup.sh is executable ───────────────────────────────────────────
ssh "$HOST" "chmod +x ${REMOTE_DIR}/startup.sh"

# ── Install systemd service ───────────────────────────────────────────────────
echo "▶ Installing systemd service..."
scp transit-display.service "${HOST}:/tmp/transit-display.service"
ssh "$HOST" "sudo mv /tmp/transit-display.service /etc/systemd/system/ && \
             sudo systemctl daemon-reload && \
             sudo systemctl enable transit-display"

# ── Restart if already running, otherwise print start instructions ────────────
if ssh "$HOST" "sudo systemctl is-active --quiet transit-display"; then
    echo "▶ Service is running — restarting..."
    ssh "$HOST" "sudo systemctl restart transit-display"
    echo "✅ Done. Service restarted."
else
    echo ""
    echo "✅ Deploy complete. To start the service:"
    echo "   ssh ${HOST}"
    echo "   sudo systemctl start transit-display"
    echo ""
    echo "   Or check status with:"
    echo "   sudo systemctl status transit-display"
fi

echo ""
echo "   Web interface will be available at: http://$(echo $HOST | cut -d@ -f2):8080"
