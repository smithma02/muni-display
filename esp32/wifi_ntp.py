"""
WiFi connection and NTP time sync for ESP32 MicroPython.
"""
import time
import network
import ntptime
import config


def connect(timeout_sec=20):
    """
    Connect to WiFi. Returns True on success, False on timeout.
    Safe to call on every boot — reconnects if needed.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return True

    print("Connecting to WiFi: {}".format(config.WIFI_SSID))
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

    deadline = time.time() + timeout_sec
    while not wlan.isconnected():
        if time.time() > deadline:
            print("WiFi connection timed out")
            return False
        time.sleep(0.25)

    print("WiFi connected:", wlan.ifconfig()[0])
    return True


def disconnect():
    """Disconnect WiFi to reduce power draw during e-paper refresh."""
    wlan = network.WLAN(network.STA_IF)
    wlan.disconnect()
    wlan.active(False)


def sync_time(retries=3):
    """
    Sync RTC to UTC via NTP. The RTC keeps time across deep sleep wakes.
    Returns True on success.

    MicroPython's RTC epoch is 2000-01-01, not 1970-01-01. ntptime handles
    this automatically — time.time() returns seconds since 2000 on MicroPython.
    """
    ntptime.host = "pool.ntp.org"
    for attempt in range(retries):
        try:
            ntptime.settime()
            print("NTP sync OK:", _utc_now_str())
            return True
        except Exception as e:
            print("NTP attempt {}/{} failed: {}".format(attempt + 1, retries, e))
            time.sleep(1)
    print("NTP sync failed")
    return False


def local_hour():
    """
    Return the current local hour (0–23) using the TZ_OFFSET_SEC from config.
    The RTC stores UTC; we add the offset here.
    """
    utc_secs = time.time()
    local_secs = utc_secs + config.TZ_OFFSET_SEC
    # MicroPython's time.localtime() uses the RTC directly (UTC on ESP32).
    # We compute local time manually to avoid relying on system TZ support.
    t = time.gmtime(local_secs)
    return t[3]  # tm_hour


def local_time_str():
    """Return current local time as a human-readable string, e.g. '3:45 PM'."""
    utc_secs = time.time()
    local_secs = utc_secs + config.TZ_OFFSET_SEC
    t = time.gmtime(local_secs)
    hour = t[3]
    minute = t[4]
    ampm = "AM" if hour < 12 else "PM"
    hour12 = hour % 12 or 12
    return "{}:{:02d} {}".format(hour12, minute, ampm)


def local_day_of_year():
    """Return the day of year (0–365) in local time, used to track maintenance."""
    utc_secs = time.time()
    local_secs = utc_secs + config.TZ_OFFSET_SEC
    t = time.gmtime(local_secs)
    return t[7]  # tm_yday


def minutes_until_arrival(utc_str):
    """
    Parse a 511.org ISO 8601 UTC timestamp and return minutes until arrival.

    Args:
        utc_str: e.g. "2025-04-08T15:30:16Z"

    Returns:
        int >= 0 (never negative)

    MicroPython note: time.mktime() treats its argument as LOCAL time, so we
    parse the UTC fields, compute the UTC epoch manually relative to the
    MicroPython epoch (2000-01-01), then subtract time.time() (also UTC).
    """
    try:
        # Parse "YYYY-MM-DDTHH:MM:SSZ"
        year   = int(utc_str[0:4])
        month  = int(utc_str[5:7])
        day    = int(utc_str[8:10])
        hour   = int(utc_str[11:13])
        minute = int(utc_str[14:16])
        second = int(utc_str[17:19])

        # time.mktime() on MicroPython treats input as LOCAL time (UTC on ESP32
        # since we don't set a system timezone). We rely on the fact that
        # MicroPython's ESP32 port keeps the RTC in UTC and time.time() is UTC
        # seconds since 2000-01-01. Using (year, month, day, hour, minute, second,
        # 0, 0) with time.mktime() gives the correct UTC epoch value on ESP32.
        arrival_epoch = time.mktime((year, month, day, hour, minute, second, 0, 0))
        now_epoch = time.time()

        diff_sec = arrival_epoch - now_epoch
        return max(0, diff_sec // 60)
    except Exception:
        return 0


def _utc_now_str():
    t = time.gmtime()
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )
