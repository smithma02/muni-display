#!/usr/bin/env python3
"""
Local rendering test for the ESP32 transit display firmware.

Runs on Python 3 (Mac/Linux) without ESP32 hardware. Fetches live data from
the 511.org API and renders the display layout to a PNG using Pillow TrueType
fonts — giving a clean, legible preview of the layout before flashing.

Note: the actual ESP32 device renders with MicroPython's built-in 8×8 bitmap
font (scaled up in integer steps), which is blockier than this preview. The
layout dimensions — column widths, row heights, text positions — are identical.

Usage:
    cd esp32/
    python3 test_render.py              # render live transit data
    python3 test_render.py --nis        # render the not-in-service screen
    python3 test_render.py -o out.png   # custom output path

Output:
    test_output.png   — preview image (480×800 portrait)

Requires: pip install Pillow requests pytz
"""

import sys
import os
import argparse
import json

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_SHARED = os.path.join(_ROOT, 'shared')

sys.path.insert(0, _HERE)     # config, etc.
sys.path.insert(0, _SHARED)   # transit_data, arrival_fmt

from transit_data import extract_arrivals
from arrival_fmt  import format_arrival_times
import config

# ── Layout constants (must match epd_render.py) ───────────────────────────────
_W        = 480
_H        = 800
_LABEL_W  = 60
_COL_W    = (_W - _LABEL_W) // 2   # 210
_HEADER_H = 60
_COLHDR_H = 40
_FOOTER_H = 30
_DATA_TOP = _HEADER_H + _COLHDR_H  # 100
_DATA_BOT = _H - _FOOTER_H         # 770

_BLACK = 0
_WHITE = 255


# ── Font loading ──────────────────────────────────────────────────────────────

def _load_font(size):
    """Load a TrueType font at the given pixel size, falling back gracefully."""
    from PIL import ImageFont

    candidates = [
        # macOS
        '/System/Library/Fonts/Helvetica.ttc',
        '/Library/Fonts/Arial.ttf',
        # Linux
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    # Last resort: Pillow's built-in bitmap font (no size param)
    return ImageFont.load_default()


def _load_bold_font(size):
    """Load a bold TrueType font, falling back to regular."""
    from PIL import ImageFont

    # (path, face_index) — .ttc collections need an explicit index to reach the
    # bold face; individual .ttf files always use index 0.
    candidates = [
        ('/Library/Fonts/Arial Bold.ttf',                                      0),
        ('/System/Library/Fonts/Helvetica.ttc',                                1),  # face 1 = Helvetica Bold
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',               0),
        ('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',       0),
        ('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',                0),
        ('/System/Library/Fonts/Helvetica.ttc',                                0),  # regular fallback
    ]
    for path, index in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=index)
            except Exception:
                continue

    return _load_font(size)


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _text_width(draw, text, font):
    """Return the rendered pixel width of text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _draw_centered(draw, text, x0, x1, y, font, fill=_BLACK):
    """Draw text horizontally centred in [x0, x1)."""
    tw = _text_width(draw, text, font)
    x  = x0 + max(0, (x1 - x0 - tw) // 2)
    draw.text((x, y), text, font=font, fill=fill)


def _strip_emoji(s):
    return ''.join(c for c in s if ord(c) < 128)


# ── Preview renderer (Pillow-based, same layout as epd_render.py) ─────────────

def render_preview(display_name, lines_data, time_str):
    """
    Render the transit display layout using Pillow TrueType fonts.
    Returns a PIL Image (480×800, mode 'L' — 8-bit greyscale for crisp B&W).
    """
    from PIL import Image, ImageDraw

    img  = Image.new('L', (_W, _H), 255)   # white background
    draw = ImageDraw.Draw(img)

    # Fonts
    f_header  = _load_bold_font(28)   # header display name + time
    f_colhdr  = _load_font(20)        # "In" / "Out" column labels
    f_label   = _load_bold_font(30)   # line label in black cell
    f_primary = _load_bold_font(38)   # primary arrival time
    f_second  = _load_font(22)        # secondary arrival times
    f_now     = _load_bold_font(30)   # "Now" badge text
    f_footer  = _load_font(14)        # footer

    # ── Header ────────────────────────────────────────────────────────────────
    h_bbox = draw.textbbox((0, 0), display_name, font=f_header)
    h_y    = (_HEADER_H - (h_bbox[3] - h_bbox[1])) // 2
    draw.text((10, h_y), display_name, font=f_header, fill=_BLACK)

    tw = _text_width(draw, time_str, f_header)
    draw.text((_W - tw - 10, h_y), time_str, font=f_header, fill=_BLACK)

    draw.line([(0, _HEADER_H - 1), (_W, _HEADER_H - 1)], fill=_BLACK, width=1)

    # ── Column headers ────────────────────────────────────────────────────────
    y0 = _HEADER_H
    draw.line([(_LABEL_W, y0), (_LABEL_W, y0 + _COLHDR_H)], fill=_BLACK, width=1)
    draw.line([(_LABEL_W + _COL_W, y0), (_LABEL_W + _COL_W, y0 + _COLHDR_H)],
              fill=_BLACK, width=1)

    in_label  = lines_data[0].get('inbound_label',  'In')  if lines_data else 'In'
    out_label = lines_data[0].get('outbound_label', 'Out') if lines_data else 'Out'

    ch_bbox = draw.textbbox((0, 0), in_label, font=f_colhdr)
    ch_h    = ch_bbox[3] - ch_bbox[1]
    ch_y    = y0 + (_COLHDR_H - ch_h) // 2
    _draw_centered(draw, in_label,  _LABEL_W, _LABEL_W + _COL_W, ch_y, f_colhdr)
    _draw_centered(draw, out_label, _LABEL_W + _COL_W, _W,       ch_y, f_colhdr)

    draw.line([(0, y0 + _COLHDR_H - 1), (_W, y0 + _COLHDR_H - 1)],
              fill=_BLACK, width=1)

    # ── Line rows ─────────────────────────────────────────────────────────────
    n     = len(lines_data)
    row_h = (_DATA_BOT - _DATA_TOP) // n if n else 0

    for i, line in enumerate(lines_data):
        ry0 = _DATA_TOP + i * row_h
        ry1 = ry0 + row_h

        # Black label cell
        draw.rectangle([(0, ry0), (_LABEL_W - 1, ry1)], fill=_BLACK)
        lbl      = line.get('label', '?')
        lbl_bbox = draw.textbbox((0, 0), lbl, font=f_label)
        lbl_x    = (_LABEL_W - (lbl_bbox[2] - lbl_bbox[0])) // 2
        lbl_y    = ry0 + (row_h - (lbl_bbox[3] - lbl_bbox[1])) // 2
        draw.text((lbl_x, lbl_y), lbl, font=f_label, fill=_WHITE)

        # Vertical dividers
        draw.line([(_LABEL_W, ry0), (_LABEL_W, ry1)], fill=_BLACK, width=1)
        draw.line([(_LABEL_W + _COL_W, ry0), (_LABEL_W + _COL_W, ry1)],
                  fill=_BLACK, width=1)

        _draw_arrival_cell(draw, line.get('times_in', 'No arrivals'),
                           _LABEL_W, ry0, _COL_W, row_h,
                           f_primary, f_second, f_now, f_colhdr)
        _draw_arrival_cell(draw, line.get('times_ot', 'No arrivals'),
                           _LABEL_W + _COL_W, ry0, _COL_W, row_h,
                           f_primary, f_second, f_now, f_colhdr)

        if i < n - 1:
            draw.line([(0, ry1), (_W, ry1)], fill=_BLACK, width=1)

    draw.line([(0, _DATA_BOT), (_W, _DATA_BOT)], fill=_BLACK, width=1)

    # ── Footer ────────────────────────────────────────────────────────────────
    foot_text = 'Last updated ' + time_str
    ft_bbox   = draw.textbbox((0, 0), foot_text, font=f_footer)
    ft_y      = _DATA_BOT + (_FOOTER_H - (ft_bbox[3] - ft_bbox[1])) // 2
    draw.text((10, ft_y), foot_text, font=f_footer, fill=_BLACK)

    return img


def _draw_arrival_cell(draw, times_str, x, y, w, h,
                       f_primary, f_second, f_now, f_noarr):
    """Draw arrival times into a cell using Pillow."""
    cleaned = _strip_emoji(times_str)
    tokens  = [t.strip() for t in cleaned.split(',') if t.strip()]

    if not tokens or tokens == ['No arrivals']:
        na_bbox = draw.textbbox((0, 0), 'No arrivals', font=f_noarr)
        na_h    = na_bbox[3] - na_bbox[1]
        na_y    = y + (h - na_h) // 2
        _draw_centered(draw, 'No arrivals', x, x + w, na_y, f_noarr)
        return

    first = tokens[0]
    rest  = tokens[1:]

    p_bbox  = draw.textbbox((0, 0), first if first != '0' else 'Now', font=f_primary)
    p_h     = p_bbox[3] - p_bbox[1]
    s_bbox  = draw.textbbox((0, 0), ', '.join(rest), font=f_second) if rest else None
    s_h     = (s_bbox[3] - s_bbox[1]) if s_bbox else 0
    gap     = 16

    total_h = p_h + (gap + s_h if rest else 0)
    start_y = y + (h - total_h) // 2

    if first == '0':
        now_bbox = draw.textbbox((0, 0), 'Now', font=f_now)
        bw = (now_bbox[2] - now_bbox[0]) + 24
        bh = (now_bbox[3] - now_bbox[1]) + 12
        bx = x + (w - bw) // 2
        by = start_y
        draw.rectangle([(bx, by), (bx + bw, by + bh)], fill=_BLACK)
        nw = now_bbox[2] - now_bbox[0]
        draw.text((bx + (bw - nw) // 2, by + 6), 'Now', font=f_now, fill=_WHITE)
        start_y += bh
    else:
        _draw_centered(draw, first, x, x + w, start_y, f_primary)
        start_y += p_h

    if rest:
        _draw_centered(draw, ', '.join(rest), x, x + w,
                       start_y + gap, f_second)


def render_not_in_service_preview(display_name):
    """Render the not-in-service screen using Pillow."""
    from PIL import Image, ImageDraw

    img  = Image.new('L', (_W, _H), 255)
    draw = ImageDraw.Draw(img)

    f_name = _load_bold_font(90)
    f_nis  = _load_bold_font(36)
    f_sub  = _load_font(24)

    # Agency name
    n_bbox = draw.textbbox((0, 0), display_name, font=f_name)
    n_h    = n_bbox[3] - n_bbox[1]
    _draw_centered(draw, display_name, 0, _W, (_H - n_h) // 2 - 80, f_name)

    # Divider
    div_y = _H // 2 + 10
    draw.line([(40, div_y), (_W - 40, div_y)],     fill=_BLACK, width=2)
    draw.line([(40, div_y + 4), (_W - 40, div_y + 4)], fill=_BLACK, width=2)

    # "NOT IN SERVICE"
    _draw_centered(draw, 'NOT IN SERVICE', 0, _W, div_y + 20, f_nis)

    # Subtitle
    _draw_centered(draw, 'Service resumes at 5:00 AM', 0, _W, div_y + 80, f_sub)

    return img


# ── Data fetch ────────────────────────────────────────────────────────────────

def _minutes_until(utc_str):
    from datetime import datetime
    dt    = datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ")
    delta = dt - datetime.utcnow()
    return max(0, int(delta.total_seconds() // 60))


def fetch_all_stops():
    import requests as _req
    stop_cache = {}
    for name, info in config.STOPS.items():
        url = (
            "https://api.511.org/transit/StopMonitoring?"
            "api_key={api_key}&agency={agency}&stopcode={id}&format=json&MaximumStopVisits=30"
        ).format(api_key=config.API_KEY, **info)
        print(f"  Fetching {name} ({info['agency']} stop {info['id']})…")
        resp = _req.get(url, timeout=10)
        resp.raise_for_status()
        raw = json.loads(resp.content.decode('utf-8-sig'))
        stop_cache[name] = extract_arrivals(raw, _minutes_until)
        print(f"    → {len(stop_cache[name])} arrivals")
    return stop_cache


def build_lines_data(stop_cache):
    lines_data = []
    for line in config.LINES:
        in_ref  = line.get('inbound_line_ref')  or line['label']
        out_ref = line.get('outbound_line_ref') or line['label']
        lines_data.append({
            'label':          line['label'],
            'times_in':       format_arrival_times(stop_cache.get(line['inbound_stop'],  []), in_ref),
            'times_ot':       format_arrival_times(stop_cache.get(line['outbound_stop'], []), out_ref),
            'inbound_label':  line.get('inbound_label',  'In'),
            'outbound_label': line.get('outbound_label', 'Out'),
        })
    return lines_data


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Preview ESP32 display rendering locally')
    parser.add_argument('--nis', action='store_true',
                        help='Render the not-in-service screen instead of live data')
    parser.add_argument('-o', '--output', default='test_output.png',
                        help='Output PNG path (default: test_output.png)')
    args = parser.parse_args()

    output = os.path.join(_HERE, args.output)

    if args.nis:
        print(f"Rendering not-in-service screen for '{config.DISPLAY_NAME}'…")
        img = render_not_in_service_preview(config.DISPLAY_NAME)
    else:
        print(f"Fetching live data from 511.org for '{config.DISPLAY_NAME}'…")
        stop_cache = fetch_all_stops()
        lines_data = build_lines_data(stop_cache)

        import pytz
        from datetime import datetime
        pacific  = pytz.timezone('America/Los_Angeles')
        time_str = datetime.now(pacific).strftime('%-I:%M %p')

        print(f"\nRendering display (time: {time_str})…")
        for ld in lines_data:
            print(f"  {ld['label']:4s}  in: {ld['times_in']!r:30s}  out: {ld['times_ot']!r}")

        img = render_preview(config.DISPLAY_NAME, lines_data, time_str)

    img.save(output)
    print(f"\nSaved: {output}  ({img.width}×{img.height} px)")

    if sys.platform == 'darwin':
        os.system(f'open "{output}"')
    elif sys.platform.startswith('linux'):
        os.system(f'xdg-open "{output}" 2>/dev/null &')


if __name__ == '__main__':
    main()
