import time
import yaml
import base64
from datetime import datetime
from zoneinfo import ZoneInfo
from muni import *
from utils import *
import platform
import server as web_server

# Detect if running on a Raspberry Pi (and not macOS)
on_raspberry_pi = platform.system() == "Linux"

print(platform.system())
print(platform.machine())
print(platform.uname().node.lower())

epd = None
if on_raspberry_pi:
    try:
        from einkUtils import *
        import threading
        result = [None]
        def _init():
            try:
                result[0] = init_epd()
            except Exception as e:
                print(f"⚠️  E-ink display init error: {e}")
        t = threading.Thread(target=_init, daemon=True)
        t.start()
        t.join(timeout=15)
        if t.is_alive():
            print("⚠️  E-ink display timed out — running in web-only mode.")
        else:
            epd = result[0]
    except Exception as e:
        print(f"⚠️  E-ink display not available: {e}")
        print("   Running in web-only mode.")

with open('config.yaml') as f:
    config = yaml.safe_load(f)

web_server.start()


def main():
    global _last_transit_data, _refresh_count

    pacific = pytz.timezone("America/Los_Angeles")
    pacific_now = datetime.now(pacific)

    current_time = pacific_now.strftime("%-I:%M %p")      # e.g., "3:45 PM"
    current_date = pacific_now.strftime("%B %-d")         # e.g., "June 15"
    last_updated = f"{current_time} : {current_date}"

    # Fetch each unique stop once
    stop_data = {
        name: get_stop_data(stop['id'], stop.get('agency', 'SF'), config['api_key'])
        for name, stop in config['stops'].items()
    }

    # Build lines list from config
    lines = []
    for line in config['lines']:
        lines.append({
            'label': line['label'],
            'times_in': get_formatted_arrival_times(stop_data[line['inbound_stop']], line.get('inbound_line_ref', line['label'])),
            'times_ot': get_formatted_arrival_times(stop_data[line['outbound_stop']], line.get('outbound_line_ref', line['label'])),
            'inbound_label': line.get('inbound_label', 'In'),
            'outbound_label': line.get('outbound_label', 'Out'),
        })

    logo_b64 = None
    if 'display_logo' in config:
        with open(config['display_logo'], 'rb') as f:
            logo_b64 = base64.b64encode(f.read()).decode('utf-8')

    formattedTimes = {
        'lines': lines,
        'current_time': last_updated,
        'display_name': config.get('display_name', 'Transit'),
        'display_logo_b64': logo_b64,
    }

    web_server.update_cache(formattedTimes)

    # Skip display update if transit data hasn't changed since last cycle
    transit_data = lines
    if transit_data == _last_transit_data:
        print("No change in transit data, skipping display update")
        return
    _last_transit_data = transit_data

    # Enable debug mode if not on a Pi
    debug = not on_raspberry_pi

    image = render_muni_times_to_html(formattedTimes, debug=debug)

    if on_raspberry_pi and epd and image:
        # Every 30 actual refreshes, run a full clear to reset accumulated ghosting
        do_clear = (_refresh_count % 30 == 0)
        display_image(epd, image, do_clear=do_clear)
        _refresh_count += 1

pacific = ZoneInfo("America/Los_Angeles")

# Track previous transit data to skip redundant display updates
_last_transit_data = None
# Count actual display refreshes to trigger a periodic full clear
_refresh_count = 0
# Track last nightly maintenance date to run it once per night at 3 AM
_last_maintenance_date = None
# Track whether the not-in-service screen has been shown tonight
_not_in_service_shown = None

# Loop forever on Pi, just once otherwise
if on_raspberry_pi:
    while True:
        now = datetime.now(pacific)
        hour = now.hour
        today = now.date()

        # Muni runs 5 AM to ~1 AM; skip the dead window (1 AM–5 AM)
        if not (1 <= hour < 5):
            main()
        else:
            # Show the not-in-service screen once when the window opens
            if epd and _not_in_service_shown != today:
                print("🌙 Displaying not-in-service screen...")
                _not_in_service_shown = today
                display_image(epd, create_not_in_service_image())

            # Run one maintenance cycle at 3 AM, once per night
            if epd and hour == 3 and _last_maintenance_date != today:
                print("🔧 Running nightly maintenance cycle...")
                _last_maintenance_date = today
                run_maintenance_cycles(epd)
        time.sleep(65)
else:
    main()
    print("Web server running at http://localhost:8080 — press Ctrl+C to stop")
    while True:
        time.sleep(65)
        main()