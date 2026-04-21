# ─── esp32/sample.config.py ───────────────────────────────────────────────────
# Copy this file to config.py and fill in your own values before uploading.
# Configuration for the ESP32 transit display.
# Mirrors the structure of config.muni.yaml — translate your existing YAML
# config here by filling in the same stop IDs, agency codes, and line labels.
#
# To find stop IDs: https://api.511.org/transit/stops?api_key=KEY&operator_id=SF
# ──────────────────────────────────────────────────────────────────────────────

# ─── WiFi ─────────────────────────────────────────────────────────────────────
WIFI_SSID     = "YourNetworkName"
WIFI_PASSWORD = "YourPassword"

# ─── 511.org API ──────────────────────────────────────────────────────────────
API_KEY = "your-511-api-key-here"

# ─── Display identity ─────────────────────────────────────────────────────────
DISPLAY_NAME = "Muni"

# ─── Timezone offset from UTC in seconds ──────────────────────────────────────
# US/Pacific Standard Time (PST) = UTC-8
# US/Pacific Daylight Time (PDT) = UTC-7  (March–November)
# Update this when daylight saving time changes, or use an NTP pool that
# provides timezone info automatically.
TZ_OFFSET_SEC = -7 * 3600   # PDT (UTC-7)

# ─── Timing ───────────────────────────────────────────────────────────────────
REFRESH_INTERVAL_MS  = 65 * 1000    # ms between display refreshes
OFF_HOURS_SLEEP_MS   = 300 * 1000   # ms to sleep during off-hours (check every 5 min)
SERVICE_START_HOUR   = 5            # service begins at 5 AM
SERVICE_END_HOUR     = 1            # service ends at 1 AM (next day)
MAINTENANCE_HOUR     = 3            # run ghost-clear cycle at 3 AM
GHOST_CLEAR_INTERVAL = 30           # full display clear every N refreshes

# ─── Stops ────────────────────────────────────────────────────────────────────
# Each stop needs an ID (from 511.org) and an agency code.
# Common agency codes: SF (Muni), BA (BART), CT (Caltrain), AC (AC Transit)
#
# Example: Castro/West Portal area (matches config.muni.yaml)
STOPS = {
    "main_inbound":  {"id": "15727", "agency": "SF"},
    "main_outbound": {"id": "16997", "agency": "SF"},
    "f_inbound":     {"id": "15651", "agency": "SF"},
    "f_outbound":    {"id": "15676", "agency": "SF"},
}

# ─── Lines ────────────────────────────────────────────────────────────────────
# label:           text shown in the line circle (e.g. "N", "F", "Red")
# inbound_stop:    key from STOPS dict above
# outbound_stop:   key from STOPS dict above
# inbound_label:   column header for inbound direction (default "In")
# outbound_label:  column header for outbound direction (default "Out")
# inbound_line_ref:  override if the API LineRef differs from label (e.g. "Red-N")
#                    omit or set to None to use label as the LineRef
# outbound_line_ref: same for outbound direction
#
# Example: SF Muni lines at Castro/West Portal (matches config.muni.yaml)
LINES = [
    {
        "label": "F",
        "inbound_stop": "f_inbound",
        "outbound_stop": "f_outbound",
        "inbound_label": "In",
        "outbound_label": "Out",
    },
    {
        "label": "J",
        "inbound_stop": "main_inbound",
        "outbound_stop": "main_outbound",
        "inbound_label": "In",
        "outbound_label": "Out",
    },
    {
        "label": "K",
        "inbound_stop": "main_inbound",
        "outbound_stop": "main_outbound",
        "inbound_label": "In",
        "outbound_label": "Out",
    },
    {
        "label": "L",
        "inbound_stop": "main_inbound",
        "outbound_stop": "main_outbound",
        "inbound_label": "In",
        "outbound_label": "Out",
    },
    {
        "label": "M",
        "inbound_stop": "main_inbound",
        "outbound_stop": "main_outbound",
        "inbound_label": "In",
        "outbound_label": "Out",
    },
    {
        "label": "N",
        "inbound_stop": "main_inbound",
        "outbound_stop": "main_outbound",
        "inbound_label": "In",
        "outbound_label": "Out",
    },
]

# ─── BART example (uncomment and adapt for BART config) ───────────────────────
# DISPLAY_NAME = "BART"
# STOPS = {
#     # Both directions share the same stop ID — only one API request is made.
#     "civic_center_nb": {"id": "CIVC", "agency": "BA"},
#     "civic_center_sb": {"id": "CIVC", "agency": "BA"},
# }
# LINES = [
#     {
#         "label": "Red",
#         "inbound_stop": "civic_center_nb",
#         "outbound_stop": "civic_center_sb",
#         "inbound_label": "NB",
#         "outbound_label": "SB",
#         "inbound_line_ref": "Red-N",
#         "outbound_line_ref": "Red-S",
#     },
# ]
