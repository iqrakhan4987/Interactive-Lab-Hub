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
pages_per_day = 312  # 312 pages = 1 full "book day" (24 hours)
pages_per_click = 13  # Each button press adds 13 pages
pages_per_hour = pages_per_day / 24  # 13 pages per hour (312/24)

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
    """Convert pages read into a time-like format (312 pages = 24 hours)"""
    if pages_read_today == 0:
        return "00:00 book-time"
    
    # Use modulo to ensure we stay within 0-311 pages (00:00-23:59)
    current_day_pages = pages_read_today % pages_per_day
    
    # Convert pages to hours and minutes
    total_minutes = (current_day_pages / pages_per_day) * 24 * 60
    book_hours = int(total_minutes // 60)
    book_minutes = int(total_minutes % 60)
    
    return f"{book_hours:02d}:{book_minutes:02d} book-time"

def get_time_period():
    """Get what part of the day we're in based on pages"""
    progress = pages_read_today / pages_per_day
    
    if progress < 0.25:
        return "Early Book-Morning"
    elif progress < 0.5:
        return "Book-Morning"  
    elif progress < 0.75:
        return "Book-Afternoon"
    else:
        return "Book-Evening"

def get_pages_until_next_day():
    """Calculate pages remaining until next book day"""
    current_day_pages = pages_read_today % pages_per_day
    pages_remaining = pages_per_day - current_day_pages
    
    if pages_remaining == pages_per_day:
        pages_remaining = 0  # Just completed a full day
    
    return pages_remaining

def get_day_progress():
    """Show progress through the current 'book day'"""
    progress_in_current_day = (pages_read_today % pages_per_day) / pages_per_day
    percentage = int(progress_in_current_day * 100)
    
    # Create a simple progress bar
    bar_length = 15
    filled = int(progress_in_current_day * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    return f"{percentage}% [{bar}]"

while True:
    # Clear screen:
    draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))

    # Handle button press to increment pages (13 pages per click)
    if not button_pin.value and not button_pressed:  # Button pressed
        pages_read_today += pages_per_click
        
        # Reset when we reach or exceed 312 pages (24:00 book-time)
        if pages_read_today >= pages_per_day:
            pages_read_today = pages_read_today % pages_per_day
            
        button_pressed = True
        time.sleep(0.2)  # Debounce
    elif button_pin.value:
        button_pressed = False

    # Get page-based time information
    pages_time = get_pages_time()
    time_period = get_time_period()
    day_progress = get_day_progress()
    pages_until_next_day = get_pages_until_next_day()
    
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
    
    # Pages until next book day
    draw.text((x, y), f"Until next book day:", font=small_font, fill="#AAAAAA")
    y += get_text_height(small_font, "Until next book day:")
    draw.text((x, y), f"{pages_until_next_day} pages", font=small_font, fill="#FF6666")
    y += get_text_height(small_font, f"{pages_until_next_day} pages") + 5
    
    # Day progress
    draw.text((x, y), "Day Progress:", font=small_font, fill="#AAAAAA")
    y += get_text_height(small_font, "Day Progress:")
    draw.text((x, y), day_progress, font=small_font, fill="#AAAAAA")
    y += get_text_height(small_font, day_progress) + 5
    
    # Display image:
    disp.image(image, rotation)
    time.sleep(0.1)