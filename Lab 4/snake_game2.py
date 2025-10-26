"""
Snake Game Version 2: A simple snake game using a joystick for movement and an encoder for menu navigation.
This version adds encoder-based control for snake movement in Level 2.
"""

import time
import digitalio
import board
import random
import sys
# New imports for PIL/ImageDraw based graphics
from PIL import Image, ImageDraw, ImageFont 
import adafruit_rgb_display.st7789 as st7789
from adafruit_seesaw import seesaw, rotaryio, digitalio as seesaw_digitalio
import qwiic_joystick

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
# Store last encoder position for direction calculation
last_encoder_move_pos = 0 

# Joystick Setup
joystick = qwiic_joystick.QwiicJoystick()
if not joystick.connected:
    print("Joystick not connected!", file=sys.stderr)
    sys.exit(1)
joystick.begin()

# ==================== GAME CONSTANTS ====================

SCREEN_WIDTH = SCREEN_WIDTH_LOGICAL  # 240
SCREEN_HEIGHT = SCREEN_HEIGHT_LOGICAL # 135
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
    # Use the same drawing context to get text bounding box
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
    """
    Get direction from rotary encoder for snake movement.
    Encoder is rotational, so it can only change direction (LEFT/RIGHT turn).
    """
    global last_encoder_move_pos
    
    pos = -encoder.position # Negative to align with typical left=smaller, right=larger values
    diff = pos - last_encoder_move_pos
    
    if abs(diff) >= 1: # Only register a change of 1 or more click
        last_encoder_move_pos = pos
        
        # Directions in order: RIGHT (0), UP (1), LEFT (2), DOWN (3)
        # We need to map the current direction to this cycle
        direction_map = ['RIGHT', 'UP', 'LEFT', 'DOWN']
        current_index = direction_map.index(current_snake_direction)
        
        # Turn clockwise (diff > 0): index increases
        if diff > 0:
            new_index = (current_index + 1) % 4
        # Turn counter-clockwise (diff < 0): index decreases
        else:
            new_index = (current_index - 1) % 4
            
        return direction_map[new_index]
        
    return None


# ==================== GAME CLASSES (No changes needed) ====================

class Snake:
    # ... (Snake class remains unchanged)
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
        # For encoder control, we *must* allow 180-degree turns as the encoder
        # dictates the *new* absolute direction 
        # NOTE: For the encoder method above, we return the *next* direction in the cycle.
        # This implementation inherently prevents 180-degree turns unless the snake
        # is only 1 cell long, which is fine for this control scheme.
        
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
    # ... (Food class remains unchanged)
    def __init__(self, snake):
        self.position = (0, 0)
        self.spawn(snake)
    
    def spawn(self, snake):
        while True:
            self.position = (random.randint(0, GRID_WIDTH - 1), 
                           random.randint(0, GRID_HEIGHT - 1))
            if self.position not in snake.body:
                break

# ==================== MENU SYSTEM (Updated draw function) ====================

class Menu:
    def __init__(self):
        self.main_options = ['LEVEL 1', 'LEVEL 2', 'LEVEL 3']
        self.control_map = ['Joystick Control', 'Encoder Control', 'Joystick Control'] # Level 1, 2, 3
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
                # Draw selection indicator
                radius = 3
                indicator_x = text_x - radius - 8 
                draw.ellipse(
                    [(indicator_x - radius, y_pos + (option_height // 2) - radius), 
                     (indicator_x + radius, y_pos + (option_height // 2) + radius)], 
                    fill=COLOR_YELLOW
                )
                
                # --- NEW: Display Control Method for the selected Level ---
                if not self.is_sub_menu:
                    control_text = self.control_map[i]
                    control_width, _ = get_text_size(FONT_SMALL, control_text)
                    control_x = (SCREEN_WIDTH - control_width) // 2
                    # Position control text slightly below the main option text
                    draw_text(control_text, control_x, y_pos + 15, FONT_SMALL, COLOR_GREEN)
            
            draw_text(option, text_x, y_pos, FONT_LARGE, color)

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

# ==================== MAIN GAME (Updated game_loop for controls) ====================

def draw_game(snake, food, score):
    # ... (draw_game function remains unchanged)
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
    
    snake = Snake()
    food = Food(snake)
    score = 0
    
    # Speed based on difficulty
    speeds = [0.18, 0.12, 0.08]
    game_speed = speeds[difficulty]
    
    # Initialize encoder tracking for the game start
    if difficulty == 1: # Level 2 uses Encoder
        last_encoder_move_pos = -encoder.position

    last_move_time = time.time()
    
    while True:
        current_time = time.time()
        
        # --- NEW: Control Input based on Difficulty ---
        direction = None
        if difficulty == 0 or difficulty == 2:  # Level 1 and Level 3 use Joystick
            direction = get_joystick_direction()
        elif difficulty == 1: # Level 2 uses Encoder
            # Encoder changes direction (turn), it does not provide absolute direction
            new_direction = get_encoder_direction(snake.direction)
            if new_direction:
                direction = new_direction
        
        snake.change_direction(direction)
        
        # Check encoder button for pause/quit (remains the same)
        if not encoder_button.value:
            time.sleep(0.2)
            if not encoder_button.value:
                # Simple pause screen: "PAUSED"
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
                    countdown()
                    score = game_loop(menu.difficulty_level)
                    
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
