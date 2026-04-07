import time 
from datetime import datetime
from zoneinfo import ZoneInfo
from jinja2 import Environment, FileSystemLoader
from muni import *
from utils import *
import platform

# Detect if running on a Raspberry Pi (and not macOS)
on_raspberry_pi = platform.system() == "Linux"

print(platform.system())
print(platform.machine())
print(platform.uname().node.lower())

if on_raspberry_pi:
    from einkUtils import *

    epd = init_epd()

# Example usage of the function
# STOP_ID_L_OWL_WESTBOUND = '16616'
# STOP_ID_L_OWL_EASTBOUND = '16617'
# STOP_ID_28_NORTHBOUND = '13394'
# STOP_ID_28_SOUTHBOUND = '13395'
STOP_ID_CIVIC_CENTER_INBD = '15727'
STOP_ID_CIVIC_CENTER_OTBD= '16997'
STOP_ID_MARKET_8ST_INBD = '15651'
STOP_ID_MARKET_8ST_OTBD = '15676'
# STOP_ID_CASTRO_INDB = '15728'
# STOP_ID_CASTRO_OTBD = '16991'
# STOP_ID_CASTRO24_INDB = '14313'
# STOP_ID_CASTRO24_OTBD = '14334'


def main():
    global _last_transit_data, _refresh_count

    # Set up Jinja environment (template folder = current directory)
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('hello.html')

    pacific = pytz.timezone("America/Los_Angeles")
    pacific_now = datetime.now(pacific)

    current_time = pacific_now.strftime("%-I:%M %p")      # e.g., "3:45 PM"
    current_date = pacific_now.strftime("%B %-d")         # e.g., "June 15"

    # Example: "June 15 — 3:45 PM"
    last_updated = f"{current_time} : {current_date}"

    stop_data_inbound = get_muni_stop_data(STOP_ID_CIVIC_CENTER_INBD)
    stop_data_outbound = get_muni_stop_data(STOP_ID_CIVIC_CENTER_OTBD)
    stop_data_f_inbound = get_muni_stop_data(STOP_ID_MARKET_8ST_INBD)
    stop_data_f_outbound = get_muni_stop_data(STOP_ID_MARKET_8ST_OTBD)
    # stop_data_inbound = get_muni_stop_data(STOP_ID_CASTRO_INDB)
    # stop_data_outbound = get_muni_stop_data(STOP_ID_CASTRO_OTBD)
    # stop_data_bus_in = get_muni_stop_data(STOP_ID_CASTRO24_INDB)
    # stop_data_bus_out = get_muni_stop_data(STOP_ID_CASTRO24_OTBD)

    # render muni stop
    formattedTimes = {
        # "times_L_zoo": get_formatted_arrival_times(get_muni_stop_data(STOP_ID_L_OWL_WESTBOUND)),
        # "times_L_em": get_formatted_arrival_times(get_muni_stop_data(STOP_ID_L_OWL_EASTBOUND), "L"),
        # "times_28_fw": get_formatted_arrival_times(get_muni_stop_data(STOP_ID_28_NORTHBOUND), "28"),
        # "times_28_dc": get_formatted_arrival_times(get_muni_stop_data(STOP_ID_28_SOUTHBOUND)),
        "times_F_in": get_formatted_arrival_times(stop_data_f_inbound, "F"),
        "times_K_in": get_formatted_arrival_times(stop_data_inbound, "K"),
        "times_L_in": get_formatted_arrival_times(stop_data_inbound, "L"),
        "times_M_in": get_formatted_arrival_times(stop_data_inbound, "M"),
        "times_J_in": get_formatted_arrival_times(stop_data_inbound, "J"),
        "times_N_in": get_formatted_arrival_times(stop_data_inbound, "N"),
        "times_K_ot": get_formatted_arrival_times(stop_data_outbound, "K"),
        "times_F_ot": get_formatted_arrival_times(stop_data_f_outbound, "F"),
        "times_L_ot": get_formatted_arrival_times(stop_data_outbound, "L"),
        "times_M_ot": get_formatted_arrival_times(stop_data_outbound, "M"),
        "times_J_ot": get_formatted_arrival_times(stop_data_outbound, "J"),
        "times_N_ot": get_formatted_arrival_times(stop_data_outbound, "N"),

        # "times_K_in": get_formatted_arrival_times(stop_data_inbound, "K"),
        # "times_K_ot": get_formatted_arrival_times(stop_data_outbound, "K"),
        # "times_L_in": get_formatted_arrival_times(stop_data_inbound, "L"),
        # "times_L_ot": get_formatted_arrival_times(stop_data_outbound, "L"),
        # "times_M_in": get_formatted_arrival_times(stop_data_inbound, "M"),
        # "times_M_ot": get_formatted_arrival_times(stop_data_outbound, "M"),
        # "times_24_in": get_formatted_arrival_times(stop_data_bus_in, "24"),
        # "times_24_ot": get_formatted_arrival_times(stop_data_bus_out, "24"),
        "current_time": last_updated
    }

    # formattedTimes = {
    #     "times_28_fw": "3, 6, 9",
    #     "times_28_dc": "2🚀, 5, 10🚀",
    #     "times_L_em": "1🦉,7,13🦉",
    #     "times_L_zoo": "4,8,12"
    # }

    # Skip display update if transit data hasn't changed since last cycle
    transit_data = {k: v for k, v in formattedTimes.items() if k != "current_time"}
    if transit_data == _last_transit_data:
        print("No change in transit data, skipping display update")
        return
    _last_transit_data = transit_data

    # Enable debug mode if not on a Pi
    debug = not on_raspberry_pi

    image = render_muni_times_to_html(formattedTimes, debug=debug)

    if on_raspberry_pi and image:
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
            if _not_in_service_shown != today:
                print("🌙 Displaying not-in-service screen...")
                _not_in_service_shown = today
                display_image(epd, create_not_in_service_image())

            # Run one maintenance cycle at 3 AM, once per night
            if hour == 3 and _last_maintenance_date != today:
                print("🔧 Running nightly maintenance cycle...")
                _last_maintenance_date = today
                run_maintenance_cycles(epd)
        time.sleep(65)
else:
    main()
    print("Program Finished")