#!/bin/bash

# Start the pigpio
sudo pigpio-master/pigpiod

# Navigate to the project directory
cd /home/pi/muni-display

# Activate virtual environment
source venv/bin/activate

# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Update Python packages
pip install --upgrade pip
pip install -r requirements.txt

# Run the main script
python3 main.py