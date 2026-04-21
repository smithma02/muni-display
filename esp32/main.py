"""
ESP32 MicroPython transit display — main entry point.

Mirrors the logic of the Raspberry Pi main.py:
  - Fetches 511.org arrival data for all configured stops
  - Renders the layout to the Waveshare 7.5" V2 e-paper display
  - Refreshes every 65 seconds during service hours (5 AM–1 AM)
  - Shows a "not in service" screen and sleeps during off-hours (1 AM–5 AM)
  - Runs a ghost-clear maintenance cycle nightly at 3 AM
  - Uses deep sleep between updates to minimise power consumption

State that must survive deep sleep is kept in RTC memory as a small JSON object.
"""

import gc
import json
import machine
import time
import urequests

import config
import wifi_ntp
from display_epd import EPD

# epd_render is imported lazily (inside _render_display / _render_not_in_service)
# to avoid loading ~73 KB of font data into heap during the WiFi/fetch phase.
from transit_data import extract_arrivals
from arrival_fmt import format_arrival_times

# ─── RTC memory helpers ───────────────────────────────────────────────────────
# RTC memory survives deep sleep but not a hard reset / power loss.
# We store a small JSON dict so field names are self-documenting.

_RTC_DEFAULTS = {
    'refresh_count':         0,
    'last_maintenance_day': -1,
    'not_in_service_shown':  False,
    'ntp_ok':                False,
}


def _load_state():
    try:
        raw = machine.RTC().memory()
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return dict(_RTC_DEFAULTS)


def _save_state(state):
    try:
        machine.RTC().memory(json.dumps(state).encode())
    except Exception as e:
        print("State save failed:", e)


def _deep_sleep(ms):
    machine.deepsleep(ms)   # does not return; restarts in setup() via main.py


# ─── Transit data fetch ───────────────────────────────────────────────────────

def _fetch_all_stops():
    """
    Fetch the 511.org API for each unique stop and return a cache dict:
      { stop_name: [{'line_ref': str, 'minutes': int}, ...] }

    Deduplicates by (stop_id, agency) so that stops sharing the same physical
    station (e.g. BART inbound/outbound at one platform) only produce a single
    API request. A 1-second pause between distinct requests avoids burst limits.
    """
    id_cache  = {}   # (id, agency) -> arrivals list
    stop_cache = {}  # stop_name    -> arrivals list

    for stop_name, stop_info in config.STOPS.items():
        key = (stop_info['id'], stop_info['agency'])

        if key in id_cache:
            stop_cache[stop_name] = id_cache[key]
            print("Reusing cached data for:", stop_name)
            continue

        # Pause between distinct API calls to avoid burst rate-limiting
        if id_cache:
            time.sleep(1)

        url = (
            "https://api.511.org/transit/StopMonitoring?"
            "api_key={}&agency={}&stopcode={}&format=json&MaximumStopVisits=6"
        ).format(config.API_KEY, stop_info['agency'], stop_info['id'])

        try:
            gc.collect()
            gc.collect()   # double-pass catches SSL session cycles from prior fetch
            print("Fetching stop:", stop_name)
            resp = urequests.get(url, timeout=15,
                                   headers={'Accept-Encoding': 'identity'})
            raw_bytes = resp.content
            resp.close()
            del resp
            gc.collect()
            # Strip UTF-8 BOM (EF BB BF) that 511.org prepends
            if raw_bytes[:3] == b'\xef\xbb\xbf':
                raw_bytes = raw_bytes[3:]
            raw = json.loads(raw_bytes)
            del raw_bytes
            gc.collect()

            arrivals = extract_arrivals(raw, wifi_ntp.minutes_until_arrival)
            del raw
            gc.collect()
            id_cache[key]          = arrivals
            stop_cache[stop_name]  = arrivals
            print("  {} arrivals for {}".format(len(arrivals), stop_name))

        except Exception as e:
            print("  Error fetching {}: {} [{}]".format(stop_name, e, type(e).__name__))
            id_cache[key]          = []
            stop_cache[stop_name]  = []
            gc.collect()

    return stop_cache


def _build_lines_data(stop_cache):
    """
    Build the lines_data list consumed by epd_render.render().
    Mirrors the lines-building loop in Pi main.py.
    """
    lines_data = []
    for line in config.LINES:
        label        = line['label']
        in_stop      = line['inbound_stop']
        out_stop     = line['outbound_stop']
        in_line_ref  = line.get('inbound_line_ref')  or label
        out_line_ref = line.get('outbound_line_ref') or label

        times_in = format_arrival_times(stop_cache.get(in_stop,  []), in_line_ref)
        times_ot = format_arrival_times(stop_cache.get(out_stop, []), out_line_ref)

        lines_data.append({
            'label':          label,
            'times_in':       times_in,
            'times_ot':       times_ot,
            'inbound_label':  line.get('inbound_label',  'In'),
            'outbound_label': line.get('outbound_label', 'Out'),
        })

    return lines_data


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    gc.collect()
    state = _load_state()

    # ── Ensure time is available ──────────────────────────────────────────────
    # We need the current hour before deciding whether to connect to WiFi at all.
    # On first boot the RTC may not have a valid time, so we always connect once.
    if not state['ntp_ok']:
        if not wifi_ntp.connect():
            print("WiFi unavailable — sleeping 60s before retry")
            _deep_sleep(60_000)
            return  # unreachable; deep_sleep restarts
        wifi_ntp.sync_time()
        state['ntp_ok'] = True
        _save_state(state)

    hour = wifi_ntp.local_hour()
    print("Local hour:", hour)

    # ── Off-hours: 1 AM–5 AM ──────────────────────────────────────────────────
    off_hours = (config.SERVICE_END_HOUR <= hour < config.SERVICE_START_HOUR)

    if off_hours:
        # Show not-in-service screen once when the window opens
        if not state['not_in_service_shown']:
            if not wifi_ntp.connect():
                _deep_sleep(60_000)
                return
            wifi_ntp.sync_time()
            wifi_ntp.disconnect()
            gc.collect()

            # Allocate buffer after WiFi stack is freed, before font imports
            _display_buf = bytearray(48000)

            print("Displaying not-in-service screen")
            import epd_render
            epd = EPD()
            epd.init()
            buf = epd_render.render_not_in_service(config.DISPLAY_NAME, _display_buf)
            del _display_buf
            epd.display(buf)
            epd.sleep()
            del epd, buf
            gc.collect()

            state['not_in_service_shown'] = True
            _save_state(state)

        # Nightly maintenance at 3 AM, once per calendar day
        today = wifi_ntp.local_day_of_year()
        if (hour == config.MAINTENANCE_HOUR
                and state['last_maintenance_day'] != today):
            print("Running nightly maintenance cycle")
            epd = EPD()
            epd.init()
            for _ in range(3):
                # Black frame
                epd.fill_black()
                time.sleep(1)
                # White frame
                epd.clear()
                time.sleep(1)
            epd.sleep()
            del epd
            gc.collect()

            state['last_maintenance_day'] = today
            _save_state(state)

        print("Off-hours: sleeping {}s".format(config.OFF_HOURS_SLEEP_MS // 1000))
        _deep_sleep(config.OFF_HOURS_SLEEP_MS)
        return   # unreachable

    # ── Service hours: fetch and render ──────────────────────────────────────
    state['not_in_service_shown'] = False

    if not wifi_ntp.connect():
        print("WiFi unavailable — sleeping 60s before retry")
        _deep_sleep(60_000)
        return

    # Re-sync NTP hourly (RTC drifts ~1 min/hr without correction)
    wifi_ntp.sync_time()

    time_str   = wifi_ntp.local_time_str()
    stop_cache = _fetch_all_stops()

    # Disconnect WiFi FIRST — frees ~30 KB of WiFi stack back to the heap.
    # Then allocate the 48 KB display buffer BEFORE importing epd_render
    # (which loads ~35 KB of font data). This ordering maximises the chance
    # of finding a contiguous 48 KB block: WiFi freed, JSON freed, no fonts yet.
    wifi_ntp.disconnect()
    gc.collect()

    lines_data = _build_lines_data(stop_cache)
    del stop_cache
    gc.collect()

    _display_buf = bytearray(48000)   # allocate before font imports fragment heap

    import epd_render
    print("Rendering display:", time_str)
    epd = EPD()
    epd.init()

    # Periodic full clear every N refreshes to combat ghosting
    if state['refresh_count'] % config.GHOST_CLEAR_INTERVAL == 0:
        print("Running periodic ghost-clear")
        epd.clear()

    buf = epd_render.render(config.DISPLAY_NAME, lines_data, time_str, _display_buf)
    del _display_buf
    epd.display(buf)
    epd.sleep()
    del epd, buf
    gc.collect()

    state['refresh_count'] += 1
    _save_state(state)

    print("Done. Sleeping {}s".format(config.REFRESH_INTERVAL_MS // 1000))
    _deep_sleep(config.REFRESH_INTERVAL_MS)


main()
