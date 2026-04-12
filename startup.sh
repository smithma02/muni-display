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
if ! dpkg -s python3-venv pigpio git > /dev/null 2>&1; then
    echo "Installing system dependencies..."
    # Wait for any other apt process to finish before proceeding
    while flock -n /var/lib/dpkg/lock-frontend echo > /dev/null 2>&1; do
        echo "Waiting for apt lock..."
        sleep 5
    done
    sudo apt-get update -q
    sudo apt-get install -y -q python3-venv pigpio
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
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update Python packages
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Run the main script
python3 main.py
