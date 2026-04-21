# Transit Display

**Transit Display** is a Python-based application designed to fetch real-time transit data and display it on an e-ink screen and a local network web page. It supports any agency available on the 511.org API (SF Muni, BART, and others).

Two compute platforms are supported:

| Platform | Description |
|----------|-------------|
| **Raspberry Pi** | Full-featured: web server, HTML rendering, easy SSH deployment. See [Pi Setup](#pi-setup) below. |
| **ESP32** | Self-contained, no Pi needed. MicroPython firmware with WiFi + deep sleep. See [`esp32/README.md`](esp32/README.md). |

## Features

- Real-time transit data via the 511.org API (supports Muni, BART, and other Bay Area agencies)
- Multi-agency support — mix stops from different agencies on the same display
- E-ink display rendering (Waveshare 7.5" V2)
- YAML-based configuration for stops, lines, agency codes, and API key
- Configurable display name and per-line direction labels
- Skips redundant display refreshes when transit data hasn't changed
- Periodic full display clear every 30 refreshes to prevent ghosting
- Nightly maintenance cycle at 3 AM to reset accumulated charge
- Not-in-service screen during the 1 AM–5 AM window
- Standalone maintenance script for manual ghosting remediation
- Local network web server with live-updating transit page (auto-refreshes every 60 seconds)
- HTML-to-image rendering via WeasyPrint and Jinja2

## Usage

```bash
python3 main.py
```

This starts both the e-ink display loop and the web server. On startup you'll see:

```
🌐 Web server started at http://0.0.0.0:8080
```

### Web Interface

The web server runs automatically as part of `main.py` — no separate process needed. Once running, open a browser and navigate to:

- **Local machine**: `http://localhost:8080`
- **On the Pi from another device**: `http://<pi-ip-address>:8080`

The page shows the same transit data as the e-ink display and refreshes arrival times every 60 seconds without a full page reload. A JSON API is also available at `/data` if you want to build on top of it.

To find your Pi's IP address:

```bash
hostname -I
```

### Local Development (without a Pi)

`main.py` detects whether it's running on a Raspberry Pi. On macOS or Linux without the Pi hardware, it runs `main()` once and exits — which is enough to verify the web output. The web server still starts, so you can load `http://localhost:8080` in a browser to preview the page.

```bash
# Install dependencies
pip install -r requirements.txt

# Run once — fetches live data, starts web server, saves hello-out.html and hello-out.bmp
python3 main.py
```

Open `http://localhost:8080` before the script finishes to see the live web view, or open `hello-out.html` to inspect the e-ink render.

### Pi Setup

Ensure your e-ink screen is connected and supported by the Waveshare driver. The systemd service starts `main.py` automatically on boot — see [Running as a Service](#running-as-a-service) below.

## Configuration

All stops, lines, and credentials are defined in a YAML config file loaded as `config.yaml`. Separate config files are provided for each agency:

- `muni.config.yaml` — SF Muni (lines F, J, K, L, M, N at Castro/West Portal)
- `config.yaml` — BART (Red, Yellow, Green, Blue at Civic Center/UN Plaza)

To switch agencies, copy or symlink the desired file to `config.yaml`.

### Config file structure

```yaml
api_key: "your-511-api-key"
display_name: "Muni"        # text shown in the display header
display_logo: "muni.png"    # optional: base64-embeds an image instead of display_name text

stops:
  main_inbound:
    id: '15727'
    agency: SF              # 511.org agency code (SF = Muni, BA = BART, etc.)
  main_outbound:
    id: '16997'
    agency: SF

lines:
  - label: "N"              # text shown in the line circle
    inbound_stop: main_inbound
    outbound_stop: main_outbound
    # inbound_label / outbound_label default to "In" / "Out" if omitted
    # inbound_line_ref / outbound_line_ref default to label if omitted
```

Each stop ID is fetched once regardless of how many lines reference it.

### `label` vs `line_ref`

Some agencies (e.g. BART) include a direction suffix in their `LineRef` values (`Red-S`, `Red-N`) that shouldn't appear in the display. Use `inbound_line_ref`/`outbound_line_ref` to specify the exact API lookup key separately from the display `label`:

```yaml
lines:
  - label: "Red"            # shown on display
    inbound_stop: civic_sb
    outbound_stop: civic_nb
    inbound_line_ref: "Red-S"   # matched against LineRef in the API response
    outbound_line_ref: "Red-N"
    inbound_label: "SB"
    outbound_label: "NB"
```

For Muni, `LineRef` matches the line letter exactly (`N`, `K`, etc.) so `inbound_line_ref`/`outbound_line_ref` can be omitted.

### Adding or Removing Lines

- **Add a line**: add an entry under `lines` with a `label`, `inbound_stop`, and `outbound_stop`. Add the stop under `stops` if it's new.
- **Remove a line**: delete the entry from `lines`. Remove the stop from `stops` if nothing else references it.
- **Change the header**: update `display_name` or set `display_logo` to an image file path.

The `hello.html` template loops over `lines` automatically — no HTML changes required.

### Agency Codes

Common 511.org agency codes:

| Agency | Code |
|--------|------|
| SF Muni | `SF` |
| BART | `BA` |
| Caltrain | `CT` |
| AC Transit | `AC` |

## Hardware

### Raspberry Pi option

| Component | Notes |
|-----------|-------|
| **Waveshare 7.5" e-ink display (V2)** | [Amazon](https://www.amazon.com/dp/B075R4QY3L) — includes the HAT that connects directly to the Pi GPIO header |
| **Raspberry Pi Zero W** | Recommended — low power, small form factor, built-in WiFi. Any Pi with a 40-pin GPIO header will work. |
| **MicroSD card** | 8GB or larger. Class 10 recommended. |
| **Picture frame (5×7")** | [Amazon](https://www.amazon.com/dp/B0CMCF8QMQ) — the display fits nicely in a standard 5×7 frame |
| **3D printed parts** | Three STL files are included — see printing notes below |

### ESP32 option

| Component | Notes |
|-----------|-------|
| **Waveshare 7.5" e-ink display (V2)** | Same display as the Pi option |
| **Waveshare e-Paper ESP32 Driver Board** | [Waveshare](https://www.waveshare.com/e-paper-esp32-driver-board.htm) — ESP32 with built-in WiFi; no separate HAT needed |

The ESP32 option is smaller and uses deep sleep for lower power draw. It does not include a web server. See [`esp32/README.md`](esp32/README.md) for full setup instructions.

### 3D Printed Parts

Print the following from the `stl/` folder:

| File | Qty | Purpose |
|------|-----|---------|
| `Transit Display Matte.stl` | 1 | Matte that holds the e-ink display in the picture frame |
| `Corner Bracket.stl` | 2 | Brackets that retain the display against the matte from behind |
| `Raspberry Pi Bracket.stl` | 1 | Mounts the Pi Zero W to the back of the frame |

### Customizing the Matte

You can print a custom overlay on regular paper and glue it to the front of the matte to add color, branding, or decorative styling to the frame. This is a simple way to match the display to your interior, add a transit agency logo, or give it a more polished look without painting the printed part.

### Assembly

1. Print all three parts above
2. Optionally print a paper overlay and glue it to the front of the matte
3. Fit the matte into the picture frame in place of the standard matte
4. Seat the e-ink display into the matte cutout and secure it with the two corner brackets
5. Connect the Waveshare HAT to the Raspberry Pi Zero W's 40-pin GPIO header
6. Route the ribbon cable from the display to the HAT
7. Mount the Pi in its bracket on the back of the frame and run a micro-USB power cable out the back

## Pi Prerequisites

### 1. Enable SPI

The Waveshare e-ink display communicates over SPI, which is disabled by default on Raspberry Pi OS. This is a one-time setup that requires a reboot.

**Option A — raspi-config (recommended):**
```bash
sudo raspi-config
# Interface Options → SPI → Enable
sudo reboot
```

**Option B — edit config directly:**

On Raspberry Pi OS Bookworm and later, the config file is at `/boot/firmware/config.txt`. On older versions it's `/boot/config.txt`.

```bash
sudo nano /boot/firmware/config.txt
```

Add or uncomment this line:
```
dtparam=spi=on
```

Then reboot:
```bash
sudo reboot
```

To confirm SPI is enabled after rebooting:
```bash
ls /dev/spi*
# Should show: /dev/spidev0.0  /dev/spidev0.1
```

### 2. System packages

The following are installed automatically by `startup.sh` on each boot:

- **`pigpio`** — GPIO library required for the Waveshare e-ink display
- **`python3-venv`** — needed to create the Python virtual environment
- **`git`** — needed to clone the Waveshare driver library (see below)

To install manually before the first run:

```bash
sudo apt-get update
sudo apt-get install -y pigpio python3-venv
```

The `pigpiod` daemon is started automatically by `startup.sh`. To start it manually:

```bash
sudo pigpiod
```

### 3. Waveshare e-Paper library

The Waveshare driver is not on PyPI and must be cloned from GitHub. `startup.sh` does this automatically on first run into `~/muni-display/e-Paper/`. To do it manually:

```bash
cd ~/muni-display
git clone --depth=1 https://github.com/waveshare/e-Paper.git
```

The driver for the 7.5" V2 display is loaded from:
`e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd/epd7in5_V2.py`

## Deploying to the Pi

A deploy script handles copying files, installing the systemd service, and preserving your existing config.

```bash
./deploy.sh <pi-host>

# Examples:
./deploy.sh 192.168.1.42
./deploy.sh pi@192.168.1.42
./deploy.sh transit.local
```

The script will:
1. Copy all project files to `~/muni-display` on the Pi
2. Copy the `images/` folder
3. Install `sample.config.yaml` as `config.yaml` **only if no config exists yet** — existing configs are left untouched
4. Install and enable the systemd service
5. Restart the service if it was already running

On first deploy, you'll need to SSH in and add your API key:

```bash
ssh pi@<ip>
nano ~/muni-display/config.yaml   # add your api_key
sudo systemctl start transit-display
```

To find the Pi's IP if you don't know it:

```bash
arp -a | grep -i raspberry
# or on the Pi itself:
hostname -I
```

## Running as a Service

A systemd service file (`transit-display.service`) is included to run the display and web server automatically on boot.

**Install on the Pi:**

```bash
sudo cp transit-display.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable transit-display
sudo systemctl start transit-display
```

**Check status / logs:**

```bash
sudo systemctl status transit-display
journalctl -u transit-display -f
```

The service waits for the network to be available before starting (`network-online.target`), ensuring the web server can bind its port and the 511.org API is reachable.

## Maintenance

To manually clear ghosting from the e-ink display, run the maintenance script on the Pi:

```bash
python3 maintenance.py
python3 maintenance.py --cycles 8 --delay 2.0   # more aggressive
```

This cycles the display through black/white patterns and finishes with a full clear. Nightly maintenance also runs automatically at 3 AM.

## Project Structure

**Shared (used by both Pi and ESP32):**
- `shared/transit_data.py` – Parses 511.org JSON into a flat list of `{line_ref, minutes}` dicts
- `shared/arrival_fmt.py` – Formats arrival times into display strings (e.g. `"2, 5, 10"`)

**Raspberry Pi:**
- `main.py` – App entry point and main loop
- `muni.py` – Fetches data from the 511.org API; delegates parsing to `shared/`
- `server.py` – Flask web server (routes `/` and `/data`, shared transit cache)
- `einkUtils.py` – E-ink display control (init, display, sleep, maintenance, not-in-service screen)
- `utils.py` – HTML/image rendering utilities
- `hello.html` – Jinja2 template for the e-ink display render
- `web.html` – Jinja2 template for the browser web view
- `config.yaml` – Active config (copy/symlink from an agency-specific config file)
- `config.muni.yaml` – Muni config (F, J, K, L, M, N at Castro/West Portal)
- `config.bart.yaml` – BART config (Red, Yellow, Green, Blue at Civic Center/UN Plaza)
- `maintenance.py` – Standalone script for manual display maintenance
- `transit-display.service` – systemd service file for running on boot
- `startup.sh` – Service entrypoint (activates venv, installs deps, runs main.py)
- `deploy.sh` – Deploy script to copy files to the Pi and install the service
- `stl/` – 3D printable parts: display matte, 2× corner brackets, and Raspberry Pi mount

**ESP32 (MicroPython, self-contained):**
- `esp32/main.py` – Entry point; fetch → render → deep sleep loop
- `esp32/config.py` – WiFi credentials, API key, stops, and lines (mirrors YAML structure)
- `esp32/display_epd.py` – UC8179 SPI driver for the Waveshare 7.5" V2
- `esp32/epd_render.py` – framebuf-based layout renderer
- `esp32/wifi_ntp.py` – WiFi connect/disconnect, NTP sync, time helpers
- `esp32/README.md` – Full ESP32 setup and flashing instructions

## Requirements

```
html2image
jinja2
Pillow
requests
WeasyPrint
pdf2image
pytz
pyyaml
flask

# Only install these on Raspberry Pi (Linux)
spidev
gpiozero
```

## License

MIT License

---
