#!/bin/bash
set -e

# Navigate to the project directory
cd /home/pi/muni-display

# Check SPI is enabled (required for e-ink display)
if [ ! -e /dev/spidev0.0 ]; then
    echo "⚠️  SPI is not enabled. Run: sudo raspi-config → Interface Options → SPI"
    echo "   Then reboot and try again."
    exit 1
fi

# Install system dependencies only if any are missing
REQUIRED_PKGS="python3-venv pigpio git python3-dev libjpeg-dev zlib1g-dev libfreetype6-dev libopenjp2-7-dev libffi-dev python3-lgpio"
if ! dpkg -s $REQUIRED_PKGS > /dev/null 2>&1; then
    echo "Installing system dependencies..."
    # Wait for any other apt process to finish before proceeding
    while flock -n /var/lib/dpkg/lock-frontend echo > /dev/null 2>&1; do
        echo "Waiting for apt lock..."
        sleep 5
    done
    sudo apt-get update -q
    sudo apt-get install -y -q $REQUIRED_PKGS
    sudo apt-get clean
fi

# Clone Waveshare e-Paper library if not already present
if [ ! -d "e-Paper" ]; then
    echo "Cloning Waveshare e-Paper library..."
    sudo apt-get install -y -q git
    git clone --depth=1 https://github.com/waveshare/e-Paper.git
fi

# Start pigpio daemon (ignore error if already running)
sudo pigpiod || true

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv --system-site-packages venv
fi

PIP=venv/bin/pip
PYTHON=venv/bin/python3

# Install/update Python packages
mkdir -p /home/pi/tmp
$PIP install --upgrade pip -q --no-cache-dir
TMPDIR=/home/pi/tmp $PIP install -r requirements.txt -q --no-cache-dir
rm -rf /home/pi/tmp

# Run the main script
$PYTHON main.py
