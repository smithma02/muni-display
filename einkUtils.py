import sys
import os
import time
from PIL import Image, ImageDraw, ImageFont
sys.path.append(os.path.expanduser('~/muni-display/e-Paper/RaspberryPi_JetsonNano/python/lib'))  # path to the driver folder

from waveshare_epd import epd7in5_V2


def init_epd():
    """
    Initializes the 7.5" Waveshare e-ink display and returns the epd object.
    Only call this once to avoid repeated slow startups.
    
    :return: Initialized EPD object
    """
    epd = epd7in5_V2.EPD()
    epd.init()
    print("🖥️ EPD initialized")
    return epd

def display_image(epd, image, do_clear=False):
    """
    Displays a PIL image directly on a 7.5" Waveshare e-ink display (800x480).
    Wakes the display with init(), optionally runs a full Clear() to combat
    ghosting, pushes the frame, then puts the display to sleep to reduce wear.

    :param image: PIL.Image.Image object
    :param do_clear: If True, run epd.Clear() before displaying (use periodically to reset ghosting)
    """
    try:
        # Ensure correct size and mode
        image = image.rotate(90, expand=True)
        image = image.resize((800, 480)).convert("1", dither=Image.NONE)

        epd.init()  # wake from sleep before each update
        if do_clear:
            epd.Clear()
            print("🧹 Ran full EPD clear to reset ghosting")
        epd.display(epd.getbuffer(image))
        epd.sleep()  # sleep immediately after to reduce wear and fading
        print("🖼️ Image displayed on e-ink screen")

    except Exception as e:
        print(f"❌ Failed to display image: {e}")

def run_maintenance_cycles(epd, cycles=3, delay=1.0):
    """
    Cycles the display through full black/white frames to combat ghosting.
    Called nightly at 3 AM and available as a standalone script.

    :param epd: EPD object (from epd7in5_V2.EPD())
    :param cycles: Number of black/white pairs to run
    :param delay: Seconds to hold each frame before switching
    """
    black = Image.new('1', (800, 480), 0)
    white = Image.new('1', (800, 480), 1)

    print(f"🔧 Running {cycles} maintenance cycles (delay={delay}s)...")
    for i in range(cycles):
        print(f"  Cycle {i + 1}/{cycles} — black")
        epd.init()
        epd.display(epd.getbuffer(black))
        time.sleep(delay)
        print(f"  Cycle {i + 1}/{cycles} — white")
        epd.init()
        epd.display(epd.getbuffer(white))
        time.sleep(delay)

    epd.init()
    epd.Clear()
    epd.sleep()
    print("✅ Maintenance complete. Display asleep.")

def create_not_in_service_image():
    """
    Creates a simple PIL image for the overnight not-in-service screen.
    Shows the Muni name and when service resumes.
    Returns a 480x800 portrait image (display_image will rotate it to landscape).
    """
    W, H = 480, 800
    img = Image.new('1', (W, H), 1)  # white background
    draw = ImageDraw.Draw(img)

    # Try common Pi system fonts, fall back to PIL default
    font_path = None
    for path in [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
    ]:
        if os.path.exists(path):
            font_path = path
            break

    if font_path:
        font_muni    = ImageFont.truetype(font_path, 130)
        font_heading = ImageFont.truetype(font_path, 52)
        font_sub     = ImageFont.truetype(font_path, 38)
    else:
        font_muni = font_heading = font_sub = ImageFont.load_default()

    def centered_x(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return (W - (bbox[2] - bbox[0])) // 2

    # "MUNI" — large, upper-center
    draw.text((centered_x("MUNI", font_muni), 200), "MUNI", font=font_muni, fill=0)

    # Divider
    draw.line([(60, 375), (420, 375)], fill=0, width=3)

    # "NOT IN SERVICE"
    draw.text((centered_x("NOT IN SERVICE", font_heading), 400), "NOT IN SERVICE",
              font=font_heading, fill=0)

    # "Service resumes at 5:00 AM"
    draw.text((centered_x("Service resumes at 5:00 AM", font_sub), 490),
              "Service resumes at 5:00 AM", font=font_sub, fill=0)

    return img