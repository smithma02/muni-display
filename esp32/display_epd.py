"""
MicroPython driver for the Waveshare 7.5" V2 e-paper display (800×480, 1-bit B/W)
driven in PORTRAIT orientation (480×800 logical pixels).

The physical panel is 800×480 in landscape. Mounting the display rotated 90°
and configuring the UC8179 controller for 480 wide × 800 tall produces a
portrait layout that matches the Raspberry Pi hello.html template's 480×800
portrait render (the Pi rotates its output; the ESP32 does not need to).

Pin assignments are fixed by the Waveshare ESP32 Driver Board PCB traces:
  MOSI/DIN : GPIO 14
  SCK/SCLK : GPIO 13
  CS       : GPIO 15
  DC       : GPIO 27
  RST      : GPIO 26
  BUSY     : GPIO 25

Translated from Waveshare's official C reference implementation for the
ESP32 Driver Board (EPD_7in5_V2.c in the Waveshare e-Paper demo repository).
"""

import time
from machine import SPI, Pin

# ─── UC8179 command codes ──────────────────────────────────────────────────────
_CMD_POWER_SETTING           = 0x01
_CMD_POWER_OFF               = 0x02
_CMD_POWER_OFF_SEQUENCE      = 0x03
_CMD_POWER_ON                = 0x04
_CMD_BOOSTER_SOFT_START      = 0x06
_CMD_DEEP_SLEEP              = 0x07
_CMD_DATA_START_TX1          = 0x10   # old / previous-frame data
_CMD_DISPLAY_REFRESH         = 0x12
_CMD_DATA_START_TX2          = 0x13   # new-frame data (shown on refresh)
_CMD_DUAL_SPI                = 0x15
_CMD_VCOM_INTERVAL           = 0x50
_CMD_TCON_SETTING            = 0x60
_CMD_RESOLUTION              = 0x61
_CMD_FLASH_MODE              = 0x65

# Physical panel dimensions — landscape (UC8179 native orientation)
# The panel has 800 source channels × 480 gate channels.
# epd_render.py rotates the portrait layout 90° in software before display.
WIDTH    = 800
HEIGHT   = 480
BUF_SIZE = WIDTH * HEIGHT // 8   # 48 000 bytes


class EPD:
    """
    Waveshare 7.5" V2 e-paper display driver.

    Usage:
        epd = EPD()
        epd.init()
        epd.clear()
        epd.display(buf)   # buf: bytearray of length BUF_SIZE
        epd.sleep()
    """

    def __init__(self):
        self._spi  = SPI(1, baudrate=4_000_000, polarity=0, phase=0,
                         sck=Pin(13), mosi=Pin(14), miso=Pin(12))
        self._cs   = Pin(15, Pin.OUT, value=1)
        self._dc   = Pin(27, Pin.OUT, value=0)
        self._rst  = Pin(26, Pin.OUT, value=1)
        self._busy = Pin(25, Pin.IN)

    # ─── Public API ───────────────────────────────────────────────────────────

    def init(self):
        """Power on and initialise the display. Call before every display update."""
        self._reset()

        self._cmd(_CMD_POWER_SETTING, b'\x07\x07\x3f\x3f')
        self._cmd(_CMD_POWER_ON)
        self._wait_busy()

        self._cmd(0x00, b'\x1f')             # panel setting: KW mode

        # Resolution: 800 wide (0x0320) × 480 tall (0x01E0) — landscape (UC8179 native)
        self._cmd(_CMD_RESOLUTION, bytes([0x03, 0x20, 0x01, 0xE0]))

        self._cmd(_CMD_DUAL_SPI, b'\x00')

        self._cmd(_CMD_VCOM_INTERVAL, b'\x10\x07')  # VCOM and data interval
        self._cmd(_CMD_TCON_SETTING,  b'\x22')       # gate/source non-overlap

    def clear(self):
        """Fill the display with white. Use between sleep cycles to prevent ghosting."""
        # This panel's OTP LUT convention: 0=white, 1=black in TX2.
        # TX1=0x00 (old frame = all white), TX2=0x00 (new frame = all white).
        self._fill_channels(0x00, 0x00)
        self._cmd(_CMD_DISPLAY_REFRESH)
        self._wait_busy()

    def fill_black(self):
        """Fill the display with black (used for maintenance cycles)."""
        # TX1=0x00 (old=white), TX2=0xFF (new=black) — panel convention 1=black.
        self._fill_channels(0x00, 0xff)
        self._cmd(_CMD_DISPLAY_REFRESH)
        self._wait_busy()

    def display(self, buf):
        """
        Push a new image to the display.

        Args:
            buf: bytearray or bytes of length BUF_SIZE (800×480/8 = 48 000 bytes).
                 Rendered with framebuf convention: 0=black pixel, 1=white pixel.
                 This driver inverts the bytes before transmission because the
                 UC8179 OTP LUT on this panel uses the opposite polarity: 0=white,
                 1=black in TX2 data.
        """
        if len(buf) != BUF_SIZE:
            raise ValueError("buf must be {} bytes (got {})".format(BUF_SIZE, len(buf)))

        self._send_tx1_zero()
        self._send_tx2_inverted(buf)   # XOR each byte with 0xFF to match panel polarity
        self._cmd(_CMD_DISPLAY_REFRESH)
        self._wait_busy()

    def sleep(self):
        """Enter deep sleep mode to minimise power draw (~μA range)."""
        self._cmd(_CMD_POWER_OFF)
        self._wait_busy()
        self._cmd(_CMD_DEEP_SLEEP, b'\xa5')

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _reset(self):
        self._rst(1)
        time.sleep_ms(20)
        self._rst(0)
        time.sleep_ms(2)
        self._rst(1)
        time.sleep_ms(20)

    def _cmd(self, cmd, data=None):
        """Send a command byte, followed by optional data bytes."""
        self._dc(0)          # DC low = command
        self._cs(0)
        self._spi.write(bytes([cmd]))
        self._cs(1)
        if data is not None:
            self._data(data)

    def _data(self, data):
        """Send data bytes (DC high)."""
        self._dc(1)
        self._cs(0)
        self._spi.write(data)
        self._cs(1)

    def _wait_busy(self, timeout_ms=10_000):
        """Block until BUSY pin goes low (display is ready)."""
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while self._busy():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                print("EPD: BUSY timeout")
                return
            time.sleep_ms(10)

    def _send_tx1_zero(self):
        """Send all-zero (all-black) data to TX1 (previous frame channel).
        The UC8179 OTP LUT only has waveforms for transitions from black,
        so TX1 must be 0x00. This matches the Waveshare C/Python reference."""
        self._dc(0)
        self._cs(0)
        self._spi.write(bytes([_CMD_DATA_START_TX1]))
        self._cs(1)
        self._dc(1)
        self._cs(0)
        chunk = b'\x00' * 256
        for _ in range(BUF_SIZE // 256):
            self._spi.write(chunk)
        remainder = BUF_SIZE % 256
        if remainder:
            self._spi.write(b'\x00' * remainder)
        self._cs(1)

    def _send_tx2(self, buf):
        """Send framebuffer data to TX2 (new frame channel)."""
        self._dc(0)
        self._cs(0)
        self._spi.write(bytes([_CMD_DATA_START_TX2]))
        self._cs(1)
        self._dc(1)
        self._cs(0)
        # Write in 256-byte chunks to minimise peak stack usage
        mv = memoryview(buf)
        for offset in range(0, BUF_SIZE, 256):
            self._spi.write(mv[offset:offset + 256])
        self._cs(1)

    def _send_tx2_inverted(self, buf):
        """Send framebuffer to TX2 with each byte XOR'd with 0xFF.
        Required because this panel's OTP LUT uses 0=white, 1=black, while
        the framebuf is rendered with the standard 0=black, 1=white convention."""
        self._dc(0)
        self._cs(0)
        self._spi.write(bytes([_CMD_DATA_START_TX2]))
        self._cs(1)
        self._dc(1)
        self._cs(0)
        mv = memoryview(buf)
        inv = bytearray(256)
        mv_inv = memoryview(inv)
        for offset in range(0, BUF_SIZE, 256):
            chunk = mv[offset:offset + 256]
            n = len(chunk)
            for i in range(n):
                inv[i] = chunk[i] ^ 0xFF
            self._spi.write(mv_inv[:n])   # write only the filled portion
        self._cs(1)

    def _fill_channels(self, tx1_byte, tx2_byte):
        """Send solid-colour data to both TX channels without allocating a 48 KB buffer."""
        chunk1 = bytes([tx1_byte]) * 256
        chunk2 = bytes([tx2_byte]) * 256

        for cmd, chunk in ((_CMD_DATA_START_TX1, chunk1), (_CMD_DATA_START_TX2, chunk2)):
            self._dc(0); self._cs(0)
            self._spi.write(bytes([cmd]))
            self._cs(1); self._dc(1); self._cs(0)
            for _ in range(BUF_SIZE // 256):
                self._spi.write(chunk)
            remainder = BUF_SIZE % 256
            if remainder:
                self._spi.write(bytes([chunk[0]]) * remainder)
            self._cs(1)
