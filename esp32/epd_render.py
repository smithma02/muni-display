"""
Layout renderer for the ESP32 transit display.

Renders transit arrival data into a framebuf.FrameBuffer (480×800 portrait,
MONO_HLSB) that matches the visual structure of the Raspberry Pi's hello.html
template (which also renders at 480×800 portrait before the Pi rotates it).

Pixel convention (matches UC8179 display_epd.py):
  0 = black, 1 = white

Text rendering uses Helvetica fonts converted by font_to_py.py:
  font_bold_36  — primary arrival numbers, line labels, "Now" badge  (36 px bold)
  font_bold_26  — header display name and time                        (26 px bold)
  font_20       — secondary arrivals, column headers                  (20 px regular)
  font_12       — footer                                              (12 px regular)

Layout (portrait 480×800):
  Y=  0– 59   Header: display name (left) + time (right)            H=60
  Y= 60– 99   Column headers: [label col] | IN  | OUT               H=40
  Y=100–769   Line rows (height split evenly among configured lines)
  Y=770–799   Footer: "Last updated HH:MM AM/PM"                    H=30

Column widths (total width = 480):
  Label  :  60 px   (x=0)
  In     : 210 px   (x=60)
  Out    : 210 px   (x=270)
"""

import framebuf
import config
import font_bold_36
import font_bold_26
import font_20
from display_epd import WIDTH, HEIGHT, BUF_SIZE

# ─── Portrait layout dimensions ───────────────────────────────────────────────
# The UC8179 only drives pixels correctly in landscape (800×480).
# We keep the entire layout in portrait coordinates (480×800) and use
# _RotatedFB to transform to landscape on every draw call.
_PORTRAIT_W = 480
_PORTRAIT_H = 800

# ─── Layout constants (portrait coordinates) ──────────────────────────────────
_LABEL_W   = 60       # width of the line-label column
_COL_W     = (_PORTRAIT_W - _LABEL_W) // 2   # = 210 px per arrival column
_HEADER_H  = 60       # header row height
_COLHDR_H  = 40       # column-header row height
_FOOTER_H  = 30       # footer row height

_DATA_TOP  = _HEADER_H + _COLHDR_H      # y where data rows start (= 100)
_DATA_BOT  = _PORTRAIT_H - _FOOTER_H   # y where data rows end   (= 770)

_BLACK = 0
_WHITE = 1


# ─── Rotated framebuffer wrapper ─────────────────────────────────────────────
class _RotatedFB:
    """
    Wraps a landscape FrameBuffer (800×480) and exposes a portrait (480×800)
    coordinate system via a 90° CW rotation.

    Rotation formula: portrait (px, py) → landscape (lx=py, ly=479-px)

    Portrait y increases downward → landscape x increases rightward (lx = py).
    Portrait x increases rightward → landscape y decreases (ly = 479 - px).

    Axes swap: portrait hline becomes landscape vline and vice-versa.
    """

    def __init__(self, fb, buf):
        self._fb    = fb
        self._buf   = buf           # raw bytearray for direct glyph writes
        self.width  = _PORTRAIT_W   # 480
        self.height = _PORTRAIT_H   # 800

    def fill(self, c):
        self._fb.fill(c)

    def pixel(self, x, y, c=None):
        lx = y                          # portrait y → landscape x
        ly = _PORTRAIT_W - 1 - x       # portrait x → landscape y (reversed)
        if c is None:
            return self._fb.pixel(lx, ly)
        self._fb.pixel(lx, ly, c)

    def fill_rect(self, x, y, w, h, c):
        # CW rotation: portrait (x, y, w, h) → landscape lx=y..y+h-1, ly=480-x-w..479-x
        # Write directly to buf to avoid MicroPython fill_rect partial-byte set_pixel bug.
        lx_s = y
        lx_e = y + h                    # exclusive
        ly_s = _PORTRAIT_W - x - w      # 480 - x - w
        ly_e = _PORTRAIT_W - x          # 480 - x (exclusive)
        buf  = self._buf
        bv   = 0xFF if c else 0x00

        bc_s = lx_s >> 3                # first byte column in lx range
        bc_e = (lx_e - 1) >> 3         # last byte column in lx range

        if bc_s == bc_e:
            # All pixels in one byte column — build a single bit mask
            bit_hi = 7 - (lx_s & 7)            # bit for lx_s (MONO_HMSB: smaller lx = higher bit)
            bit_lo = 7 - ((lx_e - 1) & 7)      # bit for lx_e-1
            mask = ((1 << (bit_hi + 1)) - 1) & ~((1 << bit_lo) - 1) & 0xFF
            clr  = 0xFF ^ mask
            for ly in range(ly_s, ly_e):
                idx = ly * _STRIDE + bc_s
                buf[idx] = (buf[idx] | mask) if c else (buf[idx] & clr)
        else:
            # Partial start byte: covers bits 0..bit_hi_s (lx_s..byte_boundary-1)
            bit_hi_s = 7 - (lx_s & 7)
            s_mask = (1 << (bit_hi_s + 1)) - 1   # bits 0..bit_hi_s
            s_clr  = 0xFF ^ s_mask
            # Partial end byte: covers bits bit_lo_e..7 (byte_boundary..lx_e-1)
            bit_lo_e = 7 - ((lx_e - 1) & 7)
            e_mask = ~((1 << bit_lo_e) - 1) & 0xFF  # bits bit_lo_e..7
            e_clr  = 0xFF ^ e_mask

            for ly in range(ly_s, ly_e):
                base = ly * _STRIDE
                buf[base + bc_s] = (buf[base + bc_s] | s_mask) if c else (buf[base + bc_s] & s_clr)
                for bc in range(bc_s + 1, bc_e):
                    buf[base + bc] = bv
                buf[base + bc_e] = (buf[base + bc_e] | e_mask) if c else (buf[base + bc_e] & e_clr)

    def hline(self, x, y, w, c):
        self.fill_rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.fill_rect(x, y, 1, h, c)


def render(display_name, lines_data, time_str, buf=None):
    """
    Build and return the full 480×800 portrait framebuffer.

    Args:
        display_name: str — e.g. "Muni"
        lines_data:   list of dicts, each with keys:
                        label, times_in, times_ot,
                        inbound_label, outbound_label
        time_str:     str — e.g. "3:45 PM"
        buf:          optional pre-allocated bytearray of length BUF_SIZE.
                      Pass one from main() to avoid a 48KB allocation on a
                      fragmented heap.

    Returns:
        bytearray of length BUF_SIZE, ready to pass to EPD.display().
    """
    if buf is None:
        buf = bytearray(BUF_SIZE)
    _lfb = framebuf.FrameBuffer(buf, WIDTH, HEIGHT, framebuf.MONO_HMSB)
    fb   = _RotatedFB(_lfb, buf)
    fb.fill(_WHITE)

    _draw_header(fb, display_name, time_str)
    _draw_column_headers(fb, lines_data)
    _draw_line_rows(fb, lines_data)
    _draw_footer(fb, time_str)

    return buf


# ─── Section drawers ──────────────────────────────────────────────────────────

def _draw_header(fb, display_name, time_str):
    """Header row: display name on left, current time on right."""
    font = font_bold_26
    fh   = font.height()
    y    = (_HEADER_H - fh) // 2

    _draw_font_text(fb, font, display_name, 8, y)

    tw = _font_text_width(font, time_str)
    _draw_font_text(fb, font, time_str, _PORTRAIT_W - tw - 8, y)

    fb.hline(0, _HEADER_H - 1, _PORTRAIT_W, _BLACK)


def _draw_column_headers(fb, lines_data):
    """Column header row: blank label cell | IN | OUT."""
    y0 = _HEADER_H

    fb.vline(_LABEL_W,            y0, _COLHDR_H, _BLACK)
    fb.vline(_LABEL_W + _COL_W,   y0, _COLHDR_H, _BLACK)

    in_label  = lines_data[0].get('inbound_label',  'In')  if lines_data else 'In'
    out_label = lines_data[0].get('outbound_label', 'Out') if lines_data else 'Out'

    font = font_20
    fh   = font.height()
    text_y = y0 + (_COLHDR_H - fh) // 2
    _draw_centered_font_text(fb, font, in_label,  _LABEL_W,           _LABEL_W + _COL_W, text_y)
    _draw_centered_font_text(fb, font, out_label, _LABEL_W + _COL_W,  _PORTRAIT_W,       text_y)

    fb.hline(0, y0 + _COLHDR_H - 1, _PORTRAIT_W, _BLACK)


def _draw_line_rows(fb, lines_data):
    """Draw one row per transit line in the data area."""
    n = len(lines_data)
    if n == 0:
        return

    row_h = (_DATA_BOT - _DATA_TOP) // n

    for i, line in enumerate(lines_data):
        y0 = _DATA_TOP + i * row_h
        y1 = y0 + row_h

        # Label cell: black fill, white label text
        fb.fill_rect(0, y0, _LABEL_W, row_h, _BLACK)
        label = line.get('label', '?')
        font  = font_bold_36
        lbl_w = _font_text_width(font, label)
        lbl_x = (_LABEL_W - lbl_w) // 2
        lbl_y = y0 + (row_h - font.height()) // 2
        _draw_font_text(fb, font, label, lbl_x, lbl_y, fg=_WHITE)

        fb.vline(_LABEL_W,          y0, row_h, _BLACK)
        fb.vline(_LABEL_W + _COL_W, y0, row_h, _BLACK)

        _draw_arrival_cell(fb, line.get('times_in', 'No arrivals'),
                           _LABEL_W, y0, _COL_W, row_h)
        _draw_arrival_cell(fb, line.get('times_ot', 'No arrivals'),
                           _LABEL_W + _COL_W, y0, _COL_W, row_h)

        if i < n - 1:
            fb.hline(0, y1, _PORTRAIT_W, _BLACK)

    fb.hline(0, _DATA_BOT, _PORTRAIT_W, _BLACK)


def _draw_arrival_cell(fb, times_str, x, y, w, h):
    """
    Render arrival times inside a cell.
    First arrival is shown large (font_bold_36); remaining are smaller (font_20).
    '0' is shown as a filled 'Now' badge.
    Emoji and non-ASCII characters are silently skipped by the glyph renderer.
    """
    tokens = [t.strip() for t in times_str.split(',') if t.strip()]
    # Strip any non-ASCII prefix tokens (e.g. emoji annotations)
    tokens = [t for t in tokens if any(c.isdigit() or c == '0' for c in t)]

    f_primary = font_bold_36
    f_second  = font_20

    if not tokens or tokens == ['No arrivals']:
        fh = f_second.height()
        ty = y + (h - fh) // 2
        _draw_centered_font_text(fb, f_second, 'No arrivals', x, x + w, ty)
        return

    first = tokens[0].strip()
    rest  = tokens[1:]

    p_h = f_primary.height()   # 36 px
    s_h = f_second.height()    # 20 px
    gap = 10

    total_h = p_h + (gap + s_h if rest else 0)
    start_y = y + (h - total_h) // 2

    if first == '0':
        badge_text = 'Now'
        bw = _font_text_width(f_primary, badge_text) + 20
        bh = p_h + 10
        bx = x + (w - bw) // 2
        by = start_y
        fb.fill_rect(bx, by, bw, bh, _BLACK)
        tw = _font_text_width(f_primary, badge_text)
        _draw_font_text(fb, f_primary, badge_text,
                        bx + (bw - tw) // 2, by + 5, fg=_WHITE)
        start_y += bh
    else:
        # Strip any leading non-digit characters (e.g. emoji left by _strip)
        num = ''.join(c for c in first if c.isdigit())
        if num:
            _draw_centered_font_text(fb, f_primary, num, x, x + w, start_y)
        start_y += p_h

    if rest:
        # Join remaining tokens, keep only digits and punctuation
        rest_str = ', '.join(''.join(c for c in t if c.isdigit()) for t in rest)
        rest_str = rest_str.strip(', ')
        if rest_str:
            _draw_centered_font_text(fb, f_second, rest_str,
                                     x, x + w, start_y + gap)


def _draw_footer(fb, time_str):
    """Footer: 'Last updated HH:MM AM/PM' left-aligned, vertically centred."""
    font = font_20
    y    = _DATA_BOT + (_FOOTER_H - font.height()) // 2
    _draw_font_text(fb, font, 'Last updated ' + time_str, 8, y)


# ─── Font rendering helpers ───────────────────────────────────────────────────

def _font_text_width(font, text):
    """Return the pixel width of text rendered in the given font module."""
    w = 0
    lo = font.min_ch()
    hi = font.max_ch()
    for ch in text:
        oc = ord(ch)
        if lo <= oc <= hi:
            _, _, cw = font.get_ch(ch)
            w += cw
    return w


_STRIDE = WIDTH >> 3   # landscape bytes per row = 800 / 8 = 100

def _draw_font_text(fb, font, text, x, y, fg=_BLACK):
    """
    Render text at portrait position (x, y) using a font_to_py font module.
    Writes directly into the raw landscape buffer stored in fb._buf, bypassing
    framebuf.pixel() to avoid MicroPython MONO_HMSB single-bit write issues.

    CW rotation: portrait (px, py) → landscape (lx=py, ly=479-px)
    MONO_HMSB: byte = ly*100 + lx//8, bit = 7 - lx%8
    """
    buf = fb._buf
    h   = font.height()
    lo  = font.min_ch()
    hi  = font.max_ch()
    cx  = x

    for ch in text:
        oc = ord(ch)
        if not (lo <= oc <= hi):
            continue
        data, _, w = font.get_ch(ch)
        pitch = (w + 7) // 8

        for row in range(h):
            # Portrait y = y+row → landscape lx = y+row (fixed for this glyph row)
            lx         = y + row
            lx_byte    = lx >> 3            # landscape column byte index
            mask       = 1 << (7 - (lx & 7))   # MONO_HMSB: bit 7 = lx%8==0
            clear_mask = 0xFF ^ mask        # mask for clearing the bit

            for col in range(w):
                if (data[row * pitch + (col >> 3)] >> (7 - (col & 7))) & 1:
                    # Portrait x = cx+col → landscape ly = 479-(cx+col)
                    ly  = _PORTRAIT_W - 1 - cx - col
                    idx = ly * _STRIDE + lx_byte
                    if fg:                  # _WHITE=1: set bit
                        buf[idx] |= mask
                    else:                   # _BLACK=0: clear bit
                        buf[idx] &= clear_mask
        cx += w


def _draw_centered_font_text(fb, font, text, x0, x1, y, fg=_BLACK):
    """Draw text horizontally centred within [x0, x1)."""
    tw = _font_text_width(font, text)
    x  = x0 + max(0, (x1 - x0 - tw) // 2)
    _draw_font_text(fb, font, text, x, y, fg=fg)


# ─── Not-in-service screen ────────────────────────────────────────────────────

def render_not_in_service(display_name, buf=None):
    """
    Overnight not-in-service screen (portrait 480×800).
    Mirrors create_not_in_service_image() in the Pi's einkUtils.py.
    """
    if buf is None:
        buf = bytearray(BUF_SIZE)
    _lfb = framebuf.FrameBuffer(buf, WIDTH, HEIGHT, framebuf.MONO_HMSB)
    fb   = _RotatedFB(_lfb, buf)
    fb.fill(_WHITE)

    # Agency name — large bold, centred
    name_y = _PORTRAIT_H // 2 - 80
    _draw_centered_font_text(fb, font_bold_36, display_name, 0, _PORTRAIT_W, name_y)

    # Double-line horizontal divider
    div_y = name_y + font_bold_36.height() + 16
    fb.hline(40, div_y,     _PORTRAIT_W - 80, _BLACK)
    fb.hline(40, div_y + 3, _PORTRAIT_W - 80, _BLACK)

    # "NOT IN SERVICE"
    nis_y = div_y + 16
    _draw_centered_font_text(fb, font_bold_26, 'NOT IN SERVICE', 0, _PORTRAIT_W, nis_y)

    # "Service resumes at 5:00 AM"
    res_y = nis_y + font_bold_26.height() + 20
    _draw_centered_font_text(fb, font_20, 'Service resumes at 5:00 AM', 0, _PORTRAIT_W, res_y)

    return buf
