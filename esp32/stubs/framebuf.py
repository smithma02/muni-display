"""
Python 3 stub for MicroPython's framebuf module.
Implements the same FrameBuffer interface so epd_render.py can run locally.

Uses Pillow for text() rendering (glyphs are close but not pixel-identical
to MicroPython's built-in font — layout dimensions are accurate).
"""

MONO_HLSB = 0
MONO_VLSB = 1
MONO_HMSB = 2


class FrameBuffer:
    """
    Mirrors MicroPython framebuf.FrameBuffer for MONO_HLSB format.
    Pixel convention: 0 = black, 1 = white (same as display_epd.py).
    """

    def __init__(self, buf, width, height, fmt=MONO_HMSB):
        self._buf    = buf
        self.width   = width
        self.height  = height

    # ── Core pixel ops ────────────────────────────────────────────────────────

    def pixel(self, x, y, color=None):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return 0
        idx    = (y * self.width + x) // 8
        bit    = 7 - (x % 8)
        if color is None:
            return (self._buf[idx] >> bit) & 1
        if color:
            self._buf[idx] |= (1 << bit)
        else:
            self._buf[idx] &= ~(1 << bit)

    def fill(self, color):
        val = 0xff if color else 0x00
        for i in range(len(self._buf)):
            self._buf[i] = val

    def fill_rect(self, x, y, w, h, color):
        x1 = max(0, x);  x2 = min(self.width,  x + w)
        y1 = max(0, y);  y2 = min(self.height, y + h)
        for row in range(y1, y2):
            for col in range(x1, x2):
                self.pixel(col, row, color)

    def hline(self, x, y, w, color):
        self.fill_rect(x, y, w, 1, color)

    def vline(self, x, y, h, color):
        self.fill_rect(x, y, 1, h, color)

    # ── Text ──────────────────────────────────────────────────────────────────

    def text(self, s, x, y, color=1):
        """
        Draw text using an 8×8 bitmap font (via Pillow).
        Each character occupies exactly 8 pixels wide × 8 pixels tall,
        matching MicroPython's built-in font dimensions.
        Non-ASCII characters are skipped (same as on device).
        """
        from PIL import Image, ImageFont

        ascii_only = ''.join(c if ord(c) < 128 else '' for c in s)
        if not ascii_only:
            return

        # Load the classic 8×8 PIL bitmap font (ships with Pillow)
        try:
            font = ImageFont.load_default()
        except Exception:
            return   # Pillow not installed — skip text silently

        # Render into a scratch image
        w_px = len(ascii_only) * 8
        img = Image.new('1', (w_px, 8), 0)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), ascii_only, fill=1, font=font)

        bg = 1 - color   # background colour
        for row in range(8):
            for col in range(w_px):
                px = img.getpixel((col, row))
                self.pixel(x + col, y + row, color if px else bg)

    # ── Export helper (not in MicroPython; for local testing only) ────────────

    def to_image(self):
        """Convert the framebuffer to a Pillow Image for saving/displaying."""
        from PIL import Image
        img = Image.new('L', (self.width, self.height))
        px = img.load()
        for row in range(self.height):
            for col in range(self.width):
                val = self.pixel(col, row)
                px[col, row] = 255 if val else 0   # 1=white, 0=black
        return img
