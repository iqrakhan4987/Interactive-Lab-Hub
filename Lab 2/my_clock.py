import subprocess
import digitalio
import board
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789
import time
from datetime import datetime, timedelta

# Configuration for CS and DC pins:
cs_pin = digitalio.DigitalInOut(board.D5) 
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None

# Config for display baudrate:
BAUDRATE = 64000000

# Setup SPI bus:
spi = board.SPI()

# Create the ST7789 display:
disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
)

# Create blank image for drawing:
height = disp.width
width = disp.height
image = Image.new("RGB", (width, height))
rotation = 90

# Get drawing object:
draw = ImageDraw.Draw(image)

# Clear screen initially:
draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))
disp.image(image, rotation)

# Constants:
padding = -2
top = padding
x = 0

# Load fonts:
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)

# Turn on backlight:
backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

# Pages Time System Configuration
pages_read_today = 0
pages_per_hour = 10  # How many pages = 1 "page-hour"
pages_per_minute = 1  # How many pages = 1 "page-minute"
daily_page_goal = 120  # Expected pages per day (like 24 hours)

# Day start time (when your "page day" begins)
day_start = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)  # 8 AM start

# Button setup
button_pin = digitalio.DigitalInOut(board.D23)
button_pin.direction = digitalio.Direction.INPUT
button_pin.pull = digitalio.Pull.UP
button_pressed = False

def get_text_height(font, text):
    """Get text height using getbbox"""
    bbox = font.getbbox(text)
    return bbox[3] - bbox[1]

def get_pages_time():
    """Convert pages read into a time-like format"""
    if pages_read_today == 0:
        return "00:00 page-time"
    
    # Convert pages to "page-hours" and "page-minutes"
    page_hours = pages_read_today // pages_per_hour
    remaining_pages = pages_read_today % pages_per_hour
    page_minutes = remaining_pages * (60 // pages_per_hour)  # Convert to minutes scale
    
    return f"{page_hours:02d}:{page_minutes:02d} page-time"

def get_time_period():
    """Get what part of the day we're in based on pages"""
    progress = pages_read_today / daily_page_goal
    
    if progress < 0.25:
        return "Early Page-Morning"
    elif progress < 0.5:
        return "Page-Morning"  
    elif progress < 0.75:
        return "Page-Afternoon"
    else:
        return "Page-Evening"

def get_day_progress():
    """Show progress through the 'page day'"""
    progress = min(pages_read_today / daily_page_goal, 1.0)
    percentage = int(progress * 100)
    
    # Create a simple progress bar
    bar_length = 15
    filled = int(progress * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    return f"{percentage}% [{bar}]"

while True:
    # Clear screen:
    draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))

    # Handle button press to increment pages (5 pages per click)
    if not button_pin.value and not button_pressed:  # Button pressed
        pages_read_today += 5
        button_pressed = True
        time.sleep(0.2)  # Debounce
    elif button_pin.value:
        button_pressed = False

    # Get page-based time information
    pages_time = get_pages_time()
    time_period = get_time_period()
    day_progress = get_day_progress()
    
    # Display information
    y = top
    
    # Main page-time display (like a clock)
    draw.text((x, y), pages_time, font=font, fill="#00FF00")
    y += get_text_height(font, pages_time) + 5
    
    # Time period (like AM/PM)
    draw.text((x, y), time_period, font=small_font, fill="#FFAA00")
    y += get_text_height(small_font, time_period) + 10
    
    # Pages count
    draw.text((x, y), f"Pages: {pages_read_today}", font=font, fill="#FFFFFF")
    y += get_text_height(font, f"Pages: {pages_read_today}") + 5
    
    # Day progress
    draw.text((x, y), "Day Progress:", font=small_font, fill="#AAAAAA")
    y += get_text_height(small_font, "Day Progress:")
    draw.text((x, y), day_progress, font=small_font, fill="#AAAAAA")
    y += get_text_height(small_font, day_progress) + 10
    
    # Instructions
    draw.text((x, y), "Press to read", font=small_font, fill="#666666")
    y += get_text_height(small_font, "Press to read")
    draw.text((x, y), "5 more pages", font=small_font, fill="#666666")
    
    # Real time (small, at bottom)
    current_time = datetime.now()
    real_time = current_time.strftime("%H:%M")
    draw.text((x, height - 20), f"Real: {real_time}", font=small_font, fill="#333333")

    # Display image:
    disp.image(image, rotation)
    time.sleep(0.1)