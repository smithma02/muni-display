#!/usr/bin/env bash
# upload.sh — Upload all ESP32 firmware files to the device via mpremote.
#
# Usage:
#   ./upload.sh                           # auto-detect port
#   ./upload.sh /dev/tty.usbmodem-0001    # specify port explicitly
#
# Run from the esp32/ directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_DIR="$(dirname "$SCRIPT_DIR")/shared"

# ── Port detection ────────────────────────────────────────────────────────────
if [[ $# -ge 1 ]]; then
    PORT="$1"
else
    # Auto-detect: prefer tty over cu (same device, tty blocks on open until connected)
    # macOS: /dev/tty.usbmodem* or /dev/tty.usbserial*
    # Linux: /dev/ttyUSB* or /dev/ttyACM*
    PORT=$(ls /dev/tty.usbmodem* /dev/tty.usbserial* /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | head -1 || true)
    if [[ -z "$PORT" ]]; then
        echo "Error: no USB-serial port found. Plug in the ESP32 or pass the port as an argument."
        echo "  Usage: $0 /dev/tty.usbmodem-XXXX"
        exit 1
    fi
    echo "Using port: $PORT"
fi

# ── Verify config.py exists ───────────────────────────────────────────────────
if [[ ! -f "$SCRIPT_DIR/config.py" ]]; then
    echo "Error: esp32/config.py not found."
    echo "  Copy the sample and fill in your values first:"
    echo "    cp sample.config.py config.py"
    exit 1
fi

# ── Verify MicroPython is running (retry a few times to catch the post-reset window) ──
echo "Press RST on the board now, then wait..."
echo ""

VERSION=""
for attempt in 1 2 3 4 5; do
    sleep 1
    if VERSION=$(mpremote connect "$PORT" exec "import sys; print(sys.version)" 2>&1) && [[ -n "$VERSION" ]]; then
        break
    fi
    echo "  Waiting for MicroPython... (attempt $attempt/5)"
    VERSION=""
done

if [[ -z "$VERSION" ]]; then
    echo ""
    echo "Error: could not connect to MicroPython."
    echo "  The device may not have MicroPython installed, or it may be in a crash loop."
    echo "  Flash MicroPython first (put board in download mode: hold BOOT, press RST, release both):"
    echo "    esptool.py --chip esp32 --port $PORT --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-*.bin"
    exit 1
fi

echo "MicroPython OK: $VERSION"
echo ""

# ── Upload (single mpremote session — avoids reconnect errors) ────────────────
# Only the files explicitly listed below are sent to the device.
# Assets such as example.png, test_output.py, stubs/, and font_to_py.py
# are development-only and are intentionally omitted.
cd "$SCRIPT_DIR"

echo "Uploading all files..."
echo ""

mpremote connect "$PORT" \
    cp config.py      : + \
    cp wifi_ntp.py    : + \
    cp display_epd.py : + \
    cp epd_render.py  : + \
    cp main.py        : + \
    cp font_bold_36.py : + \
    cp font_bold_26.py : + \
    cp font_20.py      : + \
    cp "$SHARED_DIR/transit_data.py" : + \
    cp "$SHARED_DIR/arrival_fmt.py"  : + \
    exec "import machine; machine.reset()"

echo ""
echo "Upload complete."
