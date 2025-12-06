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
# STOP_ID_CIVIC_CENTER_INBD = '15727'
# STOP_ID_CIVIC_CENTER_OTBD= '16997'
# STOP_ID_MARKET_8ST_INBD = '15651'
# STOP_ID_MARKET_8ST_OTBD = '15676'
STOP_ID_CASTRO_INDB = '15728'
STOP_ID_CASTRO_OTBD = '16991'
STOP_ID_CASTRO24_INDB = '14313'
STOP_ID_CASTRO24_OTBD = '14334'


def main():
    # Set up Jinja environment (template folder = current directory)
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('hello.html')

    pacific = pytz.timezone("America/Los_Angeles")
    pacific_now = datetime.now(pacific)

    current_time = pacific_now.strftime("%-I:%M %p")      # e.g., "3:45 PM"
    current_date = pacific_now.strftime("%B %-d")         # e.g., "June 15"

    # Example: "June 15 — 3:45 PM"
    last_updated = f"{current_time} : {current_date}"

    # stop_data_inbound = get_muni_stop_data(STOP_ID_CIVIC_CENTER_INBD)
    # stop_data_outbound = get_muni_stop_data(STOP_ID_CIVIC_CENTER_OTBD)
    # stop_data_f_inbound = get_muni_stop_data(STOP_ID_MARKET_8ST_INBD)
    # stop_data_f_outbound = get_muni_stop_data(STOP_ID_MARKET_8ST_OTBD)
    stop_data_inbound = get_muni_stop_data(STOP_ID_CASTRO_INDB)
    stop_data_outbound = get_muni_stop_data(STOP_ID_CASTRO_OTBD)
    stop_data_bus_in = get_muni_stop_data(STOP_ID_CASTRO24_INDB)
    stop_data_bus_out = get_muni_stop_data(STOP_ID_CASTRO24_OTBD)

    # render muni stop
    formattedTimes = {
        # "times_L_zoo": get_formatted_arrival_times(get_muni_stop_data(STOP_ID_L_OWL_WESTBOUND)),
        # "times_L_em": get_formatted_arrival_times(get_muni_stop_data(STOP_ID_L_OWL_EASTBOUND), "L"),
        # "times_28_fw": get_formatted_arrival_times(get_muni_stop_data(STOP_ID_28_NORTHBOUND), "28"),
        # "times_28_dc": get_formatted_arrival_times(get_muni_stop_data(STOP_ID_28_SOUTHBOUND)),
        # "times_F_in": get_formatted_arrival_times(stop_data_f_inbound, "F"),
        # "times_K_in": get_formatted_arrival_times(stop_data_inbound, "K"),
        # "times_L_in": get_formatted_arrival_times(stop_data_inbound, "L"),
        # "times_M_in": get_formatted_arrival_times(stop_data_inbound, "M"),
        # "times_J_in": get_formatted_arrival_times(stop_data_inbound, "J"),
        # "times_N_in": get_formatted_arrival_times(stop_data_inbound, "N"),
        # "times_K_ot": get_formatted_arrival_times(stop_data_outbound, "K"),
        # "times_F_ot": get_formatted_arrival_times(stop_data_f_outbound, "F"),
        # "times_L_ot": get_formatted_arrival_times(stop_data_outbound, "L"),
        # "times_M_ot": get_formatted_arrival_times(stop_data_outbound, "M"),
        # "times_J_ot": get_formatted_arrival_times(stop_data_outbound, "J"),
        # "times_N_ot": get_formatted_arrival_times(stop_data_outbound, "N"),
        "times_K_in": get_formatted_arrival_times(stop_data_inbound, "K"),
        "times_K_ot": get_formatted_arrival_times(stop_data_outbound, "K"),
        "times_L_in": get_formatted_arrival_times(stop_data_inbound, "L"),
        "times_L_ot": get_formatted_arrival_times(stop_data_outbound, "L"),
        "times_M_in": get_formatted_arrival_times(stop_data_inbound, "M"),
        "times_M_ot": get_formatted_arrival_times(stop_data_outbound, "M"),
        "times_24_in": get_formatted_arrival_times(stop_data_bus_in, "24"),
        "times_24_ot": get_formatted_arrival_times(stop_data_bus_out, "24"),
        "current_time": last_updated
    }

    # formattedTimes = {
    #     "times_28_fw": "3, 6, 9",
    #     "times_28_dc": "2🚀, 5, 10🚀",
    #     "times_L_em": "1🦉,7,13🦉",
    #     "times_L_zoo": "4,8,12"
    # }

    # Enable debug mode if not on a Pi
    debug = not on_raspberry_pi

    image = render_muni_times_to_html(formattedTimes, debug=debug)

    if on_raspberry_pi and image:
        display_image(epd, image)

pacific = ZoneInfo("America/Los_Angeles")

# Loop forever on Pi, just once otherwise
if on_raspberry_pi:
    while True:

        current_time = datetime.now(pacific).strftime("%-I:%M %p")
        # Muni only runs from 5 AM to 1 AM
        # Don't refresh outside of these hours
        if current_time < "5:00 AM" or current_time > "1:00 AM":
            main()
        else:
            print("Muni is not in service")
        time.sleep(65)
else:
    main()
    print("Program Finished")