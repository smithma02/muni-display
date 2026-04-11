# Transit Display

**Transit Display** is a Python-based application designed to fetch real-time transit data and display it on an e-ink screen. It supports any agency available on the 511.org API (SF Muni, BART, and others). This project is ideal for Raspberry Pi setups with Waveshare displays, offering a low-power, always-on transit dashboard.

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
- HTML-to-image rendering via WeasyPrint and Jinja2

## Usage

```bash
python3 main.py
```

Ensure your e-ink screen is connected and supported by the Waveshare driver.

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

## Maintenance

To manually clear ghosting from the e-ink display, run the maintenance script on the Pi:

```bash
python3 maintenance.py
python3 maintenance.py --cycles 8 --delay 2.0   # more aggressive
```

This cycles the display through black/white patterns and finishes with a full clear. Nightly maintenance also runs automatically at 3 AM.

## Project Structure

- `main.py` – App entry point and main loop
- `muni.py` – Fetches and parses arrival data from the 511.org API (any agency)
- `einkUtils.py` – E-ink display control (init, display, sleep, maintenance, not-in-service screen)
- `utils.py` – HTML/image rendering utilities
- `hello.html` – Jinja2 template for the transit display
- `config.yaml` – Active config (copy/symlink from an agency-specific config file)
- `muni.config.yaml` – Muni config (F, J, K, L, M, N at Castro/West Portal)
- `maintenance.py` – Standalone script for manual display maintenance

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

# Only install these on Raspberry Pi (Linux)
spidev
gpiozero
```

## License

MIT License

---
