"""
E-ink display maintenance script.
Run this manually on the Pi to clear accumulated ghosting by cycling the
display through multiple full black/white frames.

Usage:
    python3 maintenance.py
    python3 maintenance.py --cycles 8   # more aggressive, for heavy ghosting
    python3 maintenance.py --cycles 12 --delay 2
"""
import sys
import os
import argparse

sys.path.append(os.path.expanduser('~/muni-display/e-Paper/RaspberryPi_JetsonNano/python/lib'))  # path to the driver folder

from waveshare_epd import epd7in5_V2
from einkUtils import run_maintenance_cycles


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=4,
                        help="Number of black/white cycles (default 4, use 8+ for heavy ghosting)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds to hold each black/white frame (default 1.0)")
    args = parser.parse_args()

    epd = epd7in5_V2.EPD()
    run_maintenance_cycles(epd, args.cycles, args.delay)
