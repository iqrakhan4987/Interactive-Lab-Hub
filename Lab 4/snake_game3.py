"""
Snake Game Version 3: A simple snake game using a joystick, rotary encoder, and accelerometer for movement and menu navigation.
Level 1: Joystick Control
Level 2: Encoder Control
Level 3: Accelerometer Control  
"""

import time
import digitalio
import board
import random
import sys
from PIL import Image, ImageDraw, ImageFont 
import adafruit_rgb_display.st7789 as st7789
from adafruit_seesaw import seesaw, rotaryio, digitalio as seesaw_digitalio
import qwiic_joystick
import adafruit_lsm6ds.lsm6ds3 as lsm6ds # Accelerometer import

# ==================== HARDWARE SETUP ====================

# Display Setup (ST7789)
cs_pin = digitalio.DigitalInOut(board.D5) 
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None
BAUDRATE = 64000000
spi = board.SPI()

# Create the ST7789 display with its physical dimensions
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

# --- LANDSCAPE CONFIGURATION ---
SCREEN_HEIGHT_LOGICAL = disp.width    # 135
SCREEN_WIDTH_LOGICAL = disp.height     # 240
image = Image.new("RGB", (SCREEN_WIDTH_LOGICAL, SCREEN_HEIGHT_LOGICAL))
rotation = 90

# Get drawing object:
draw = ImageDraw.Draw(image)

# Clear screen initially:
draw.rectangle((0, 0, SCREEN_WIDTH_LOGICAL, SCREEN_HEIGHT_LOGICAL), outline=0, fill=(0, 0, 0))
disp.image(image, rotation)

# Turn on backlight:
backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

# Encoder Setup
encoder_board = seesaw.Seesaw(board.I2C(), addr=0x36)
encoder_board.pin_mode(24, encoder_board.INPUT_PULLUP)
encoder_button = seesaw_digitalio.DigitalIO(encoder_board, 24)
encoder = rotaryio.IncrementalEncoder(encoder_board)
last_encoder_move_pos = 0 

# Joystick Setup
joystick = qwiic_joystick.QwiicJoystick()
if not joystick.connected:
    print("Joystick not connected!", file=sys.stderr)
joystick.begin()

# --- ACCELEROMETER SETUP ---
try:
    i2c = board.I2C() 
    sensor = lsm6ds.LSM6DS3(i2c)
    print("LSM6DS3 Accelerometer initialized.")
except ValueError:
    print("LSM6DS3 Accelerometer not found, Level 3 control will not work.", file=sys.stderr)
    sensor = None 

# ==================== GAME CONSTANTS ====================

SCREEN_WIDTH = SCREEN_WIDTH_LOGICAL
SCREEN_HEIGHT = SCREEN_HEIGHT_LOGICAL
CELL_SIZE = 6
GRID_WIDTH = SCREEN_WIDTH // CELL_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // CELL_SIZE

# Load fonts:
try:
    FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    FONT_SIZE_LARGE = 18
    FONT_SIZE_SMALL = 14
    FONT_LARGE = ImageFont.truetype(FONT_PATH, FONT_SIZE_LARGE)
    FONT_SMALL = ImageFont.truetype(FONT_PATH, FONT_SIZE_SMALL)
except IOError:
    print("Default font not found. Using default PIL font.")
    FONT_LARGE = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()

# Colors (as RGB tuples for PIL)
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_BLUE = (0, 100, 255)
COLOR_YELLOW = (255, 255, 0)

# Joystick thresholds
JOY_CENTER = 512
JOY_THRESHOLD = 200

# Accelerometer threshold
ACCEL_THRESHOLD = 3.0 

# ==================== HELPER FUNCTIONS ====================

def draw_cell(x, y, color):
    """Draw a single cell on the grid using ImageDraw"""
    px = x * CELL_SIZE
    py = y * CELL_SIZE
    draw.rectangle(
        [(px, py), (px + CELL_SIZE - 1, py + CELL_SIZE - 1)], 
        fill=color, 
        outline=color
    )

def draw_text(text, x, y, font, color):
    """Draw text string using ImageDraw"""
    draw.text((x, y), text, font=font, fill=color)

def get_text_size(font, text):
    """Get text width and height using getbbox for PIL font"""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2], bbox[3] - bbox[1]

def get_joystick_direction():
    """Get direction from joystick"""
    x = joystick.horizontal
    y = joystick.vertical
    
    if abs(x - JOY_CENTER) > abs(y - JOY_CENTER):
        if x < JOY_CENTER - JOY_THRESHOLD:
            return 'LEFT'
        elif x > JOY_CENTER + JOY_THRESHOLD:
            return 'RIGHT'
    else:
        if y < JOY_CENTER - JOY_THRESHOLD:
            return 'UP'
        elif y > JOY_CENTER + JOY_THRESHOLD:
            return 'DOWN'
    return None

def get_encoder_direction(current_snake_direction):
    """Get direction from rotary encoder for snake movement."""
    global last_encoder_move_pos
    
    pos = -encoder.position
    diff = pos - last_encoder_move_pos
    
    if abs(diff) >= 1:
        last_encoder_move_pos = pos
        
        direction_map = ['RIGHT', 'UP', 'LEFT', 'DOWN']
        current_index = direction_map.index(current_snake_direction)
        
        if diff > 0: # Clockwise
            new_index = (current_index + 1) % 4
        else: # Counter-clockwise
            new_index = (current_index - 1) % 4
            
        return direction_map[new_index]
        
    return None

def get_accelerometer_direction():
    """
    Get direction from accelerometer (LSM6DS3) based on tilt.
    Y-axis directions are flipped as requested.
    Returns: 'UP', 'DOWN', 'LEFT', 'RIGHT', or None
    """
    if sensor is None:
        return None
        
    accel_x, accel_y, _ = sensor.acceleration 
    
    if abs(accel_x) > abs(accel_y):
        if abs(accel_x) > ACCEL_THRESHOLD:
            if accel_x > 0:
                return 'RIGHT'
            else:
                return 'LEFT'
    else:
        if abs(accel_y) > ACCEL_THRESHOLD:
            # Y-axis directions are flipped:
            if accel_y > 0:
                return 'UP' # Tilting forward (positive Y) now means UP
            else:
                return 'DOWN' # Tilting backward (negative Y) now means DOWN
    return None

# ==================== GAME CLASSES ====================

class Snake:
    def __init__(self):
        self.reset()
    
    def reset(self):
        center_x = GRID_WIDTH // 2
        center_y = GRID_HEIGHT // 2
        self.body = [(center_x, center_y), (center_x - 1, center_y), (center_x - 2, center_y)]
        self.direction = 'RIGHT'
        self.grow_pending = 0
    
    def move(self):
        head_x, head_y = self.body[0]
        
        if self.direction == 'UP':
            new_head = (head_x, head_y - 1)
        elif self.direction == 'DOWN':
            new_head = (head_x, head_y + 1)
        elif self.direction == 'LEFT':
            new_head = (head_x - 1, head_y)
        else:  # RIGHT
            new_head = (head_x + 1, head_y)
        
        self.body.insert(0, new_head)
        
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()
    
    def change_direction(self, new_direction):
        opposites = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}
        if new_direction and opposites.get(new_direction) != self.direction:
            self.direction = new_direction
    
    def check_collision(self):
        head_x, head_y = self.body[0]
        
        if head_x < 0 or head_x >= GRID_WIDTH or head_y < 0 or head_y >= GRID_HEIGHT:
            return True
        
        if self.body[0] in self.body[1:]:
            return True
        
        return False
    
    def eat(self):
        self.grow_pending += 3

class Food:
    # FIX: Corrected __init__ to accept the 'snake' object to resolve TypeError.
    def __init__(self, snake): 
        self.position = (0, 0)
        self.spawn(snake)
    
    def spawn(self, snake):
        while True:
            self.position = (random.randint(0, GRID_WIDTH - 1), 
                           random.randint(0, GRID_HEIGHT - 1))
            if self.position not in snake.body:
                break

# ==================== MENU SYSTEM ====================

class Menu:
    def __init__(self):
        self.main_options = ['LEVEL 1', 'LEVEL 2', 'LEVEL 3']
        self.control_map = ['Joystick Control', 'Encoder Control', 'Accelerometer Control'] 
        self.sub_options = ['START GAME', 'GO BACK', 'QUIT']
        
        self.current_options = self.main_options
        self.selected = 0
        self.last_encoder_pos = 0
        self.difficulty_level = 0
        self.is_sub_menu = False
    
    def update(self):
        pos = -encoder.position
        diff = pos - self.last_encoder_pos
        
        if diff != 0:
            self.selected = (self.selected + diff) % len(self.current_options)
            self.last_encoder_pos = pos
            return True
        return False
    
    def select(self):
        selection = self.current_options[self.selected]
        
        if not self.is_sub_menu:
            self.difficulty_level = self.selected
            self.current_options = self.sub_options
            self.selected = 0
            self.is_sub_menu = True
            return 'GOTO_SUB_MENU'
        
        else:
            if selection == 'START GAME':
                return 'START'
            elif selection == 'GO BACK':
                self.current_options = self.main_options
                self.selected = self.difficulty_level
                self.is_sub_menu = False
                return 'GOTO_MAIN_MENU'
            elif selection == 'QUIT':
                return 'QUIT'

    def draw(self):
        global image, draw
        draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill=COLOR_BLACK)
        
        # Title
        title_text = "MENU" if not self.is_sub_menu else self.main_options[self.difficulty_level]
        title_width, title_height = get_text_size(FONT_LARGE, title_text)
        title_x = (SCREEN_WIDTH - title_width) // 2 
        draw_text(title_text, title_x, 10, FONT_LARGE, COLOR_YELLOW if not self.is_sub_menu else COLOR_GREEN)
        
        options_to_draw = self.current_options
        start_y = 40
        
        for i, option in enumerate(options_to_draw):
            color = COLOR_WHITE
            
            option_width, option_height = get_text_size(FONT_LARGE, option)
            text_x = (SCREEN_WIDTH - option_width) // 2
            y_pos = start_y + i * 25
            
            if i == self.selected:
                color = COLOR_YELLOW
                radius = 3
                indicator_x = text_x - radius - 8 
                draw.ellipse(
                    [(indicator_x - radius, y_pos + (option_height // 2) - radius), 
                     (indicator_x + radius, y_pos + (option_height // 2) + radius)], 
                    fill=COLOR_YELLOW
                )
                
                # Display Control Method
                if not self.is_sub_menu:
                    control_text = self.control_map[i]
                    control_width, _ = get_text_size(FONT_SMALL, control_text)
                    control_x = (SCREEN_WIDTH - control_width) // 2
                    draw_text(control_text, control_x, y_pos + 15, FONT_SMALL, COLOR_GREEN)
            
            draw_text(option, text_x, y_pos, FONT_LARGE, color)

# ==================== TUTORIAL FUNCTION ====================

def accelerometer_tutorial():
    global image, draw, disp, rotation
    
    # Check for sensor availability
    if sensor is None:
        draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill=COLOR_RED)
        fail_text = "ACCEL SENSOR MISSING"
        fw, fh = get_text_size(FONT_LARGE, fail_text)
        draw_text(fail_text, (SCREEN_WIDTH - fw) // 2, (SCREEN_HEIGHT - fh) // 2, FONT_LARGE, COLOR_WHITE)
        disp.image(image, rotation)
        time.sleep(2)
        return False # Tutorial failed (sensor missing)

    # Tutorial instructions
    instruction = "TILT TO MOVE. PRESS BUTTON TO START."
    
    while True:
        draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill=COLOR_BLACK)
        
        # Draw instructions at the top
        iw, ih = get_text_size(FONT_SMALL, instruction)
        draw_text(instruction, (SCREEN_WIDTH - iw) // 2, 10, FONT_SMALL, COLOR_WHITE)

        # Get current tilt direction
        direction = get_accelerometer_direction()
        
        # Display the detected direction prominently
        if direction:
            dir_text = direction
            color = COLOR_GREEN
        else:
            dir_text = "CENTERED"
            color = COLOR_YELLOW

        dw, dh = get_text_size(FONT_LARGE, dir_text)
        draw_text(dir_text, (SCREEN_WIDTH - dw) // 2, (SCREEN_HEIGHT - dh) // 2, FONT_LARGE, color)

        # Draw a simple representation of the acceleration values (optional, for debugging/visual flair)
        try:
            accel_x, accel_y, _ = sensor.acceleration
            accel_info = f"X:{accel_x:.1f} Y:{accel_y:.1f} (THR: {ACCEL_THRESHOLD})"
            draw_text(accel_info, 10, SCREEN_HEIGHT - 20, FONT_SMALL, COLOR_BLUE)
        except Exception:
            pass # Ignore sensor read failure during tutorial

        disp.image(image, rotation)
        
        # Check encoder button press to exit tutorial and start game
        if not encoder_button.value:
            time.sleep(0.2) # Debounce
            if not encoder_button.value:
                return True # Tutorial successful, ready for game

        time.sleep(0.05)

# ==================== COUNTDOWN ====================

def countdown():
    global image, draw
    draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill=COLOR_BLACK)

    for count in range(3, 0, -1):
        draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill=COLOR_BLACK)
        count_str = str(count)
        count_width, count_height = get_text_size(FONT_LARGE, count_str)
        
        x = (SCREEN_WIDTH - count_width) // 2 
        y = (SCREEN_HEIGHT - count_height) // 2
        
        draw_text(count_str, x, y, FONT_LARGE, COLOR_RED)
        disp.image(image, rotation)
        time.sleep(1)
    
    draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill=COLOR_BLACK)
    go_text = "GO!"
    go_width, go_height = get_text_size(FONT_LARGE, go_text)
    go_x = (SCREEN_WIDTH - go_width) // 2 
    draw_text(go_text, go_x, y, FONT_LARGE, COLOR_GREEN)
    disp.image(image, rotation)
    time.sleep(0.5)

# ==================== MAIN GAME ====================

def draw_game(snake, food, score):
    global image, draw
    draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill=COLOR_BLACK)
    
    for i, (x, y) in enumerate(snake.body):
        color = COLOR_GREEN if i == 0 else COLOR_BLUE
        draw_cell(x, y, color)
    
    draw_cell(food.position[0], food.position[1], COLOR_RED)
    
    max_len = SCREEN_WIDTH - 20
    bar_len = min(score * 5, max_len)
    draw.rectangle([(10, 3), (10 + bar_len, 6)], fill=COLOR_YELLOW)

def game_loop(difficulty):
    global image, draw, disp, rotation, last_encoder_move_pos
    
    # Check for sensor availability (only needed for Level 3)
    if difficulty == 2 and sensor is None:
        return -1 

    snake = Snake()
    food = Food(snake) # Correctly instantiated with snake object
    score = 0
    
    speeds = [0.18, 0.12, 0.08]
    game_speed = speeds[difficulty]
    
    if difficulty == 1:
        last_encoder_move_pos = -encoder.position

    last_move_time = time.time()
    
    while True:
        current_time = time.time()
        
        direction = None
        
        # --- CONTROL INPUT LOGIC ---
        if difficulty == 0:  # Level 1: Joystick
            direction = get_joystick_direction()
        elif difficulty == 1: # Level 2: Encoder
            new_direction = get_encoder_direction(snake.direction)
            if new_direction:
                direction = new_direction
        elif difficulty == 2: # Level 3: Accelerometer
            direction = get_accelerometer_direction()
        
        snake.change_direction(direction)
        
        # Check encoder button for pause/quit
        if not encoder_button.value:
            time.sleep(0.2)
            if not encoder_button.value:
                pause_text = "PAUSED"
                pw, ph = get_text_size(FONT_LARGE, pause_text)
                draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill=COLOR_BLACK)
                draw_text(pause_text, (SCREEN_WIDTH - pw) // 2, (SCREEN_HEIGHT - ph) // 2, FONT_LARGE, COLOR_RED)
                disp.image(image, rotation)
                
                start_pause_time = time.time()
                while not encoder_button.value:
                    if time.time() - start_pause_time > 1:
                        return score
                    time.sleep(0.01)

                while not encoder_button.value:
                    time.sleep(0.01)
                time.sleep(0.2)
                
                last_move_time = time.time()

        # Move snake at fixed intervals
        if current_time - last_move_time >= game_speed:
            snake.move()
            last_move_time = current_time
            
            # Check collision
            if snake.check_collision():
                for _ in range(3):
                    draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill=COLOR_RED)
                    disp.image(image, rotation)
                    time.sleep(0.15)
                    draw_game(snake, food, score)
                    disp.image(image, rotation)
                    time.sleep(0.15)
                return score
            
            # Check food
            if snake.body[0] == food.position:
                snake.eat()
                score += 1
                food.spawn(snake)
        
        draw_game(snake, food, score)
        disp.image(image, rotation)
        time.sleep(0.01)

# ==================== MAIN ====================

def main():
    global image, draw, disp, rotation
    menu = Menu()
    
    while True:
        menu.draw()
        disp.image(image, rotation)
        last_button_state = encoder_button.value
        
        while True:
            if menu.update():
                menu.draw()
                disp.image(image, rotation)
            
            if not encoder_button.value and last_button_state:
                time.sleep(0.2)
                selection_action = menu.select()
                
                if selection_action in ['GOTO_SUB_MENU', 'GOTO_MAIN_MENU']:
                    menu.draw()
                    disp.image(image, rotation)
                    
                elif selection_action == 'START':
                    
                    if menu.difficulty_level == 2:
                        # --- Run Tutorial for Level 3 ---
                        if not accelerometer_tutorial():
                            score = -1
                        else:
                            countdown()
                            score = game_loop(menu.difficulty_level)
                    else:
                        countdown()
                        score = game_loop(menu.difficulty_level)
                    
                    if score != -1:
                        # Show score briefly
                        draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill=COLOR_BLACK)
                        score_text = f"SCORE: {score}"
                        sw, sh = get_text_size(FONT_LARGE, score_text)
                        x_pos = (SCREEN_WIDTH - sw) // 2
                        y_pos = (SCREEN_HEIGHT - sh) // 2
                        draw_text(score_text, x_pos, y_pos, FONT_LARGE, COLOR_YELLOW)
                        disp.image(image, rotation)

                        time.sleep(2)
                    
                    menu.current_options = menu.main_options
                    menu.selected = menu.difficulty_level
                    menu.is_sub_menu = False
                    break

                elif selection_action == 'QUIT':
                    draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill=COLOR_BLACK)
                    disp.image(image, rotation)
                    backlight.value = False
                    sys.exit(0)
            
            last_button_state = encoder_button.value
            time.sleep(0.01)

if __name__ == '__main__':
    try:
        print("Snake Game Starting...")
        main()
    except KeyboardInterrupt:
        draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill=COLOR_BLACK)
        disp.image(image, rotation)
        backlight.value = False
        print("\nGame ended")
        sys.exit(0)