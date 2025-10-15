"""
Snake Game for Raspberry Pi with MiniPiTFT, Joystick, and Rotary Encoder
- Display: MiniPiTFT ST7789 (135x240)
- Controls: Qwiic Joystick for snake movement
- Menu: Rotary Encoder for navigation
"""

import time
import digitalio
import board
import random
from adafruit_rgb_display.rgb import color565
import adafruit_rgb_display.st7789 as st7789
from adafruit_seesaw import seesaw, rotaryio, digitalio as seesaw_digitalio
import qwiic_joystick
import sys

# ==================== HARDWARE SETUP ====================

# Display Setup
cs_pin = digitalio.DigitalInOut(board.D5)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None
BAUDRATE = 64000000

spi = board.SPI()
display = st7789.ST7789(
    spi, cs=cs_pin, dc=dc_pin, rst=reset_pin,
    baudrate=BAUDRATE, width=135, height=240,
    x_offset=53, y_offset=40
)

backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output(value=True)

# Encoder Setup
encoder_board = seesaw.Seesaw(board.I2C(), addr=0x36)
encoder_board.pin_mode(24, encoder_board.INPUT_PULLUP)
encoder_button = seesaw_digitalio.DigitalIO(encoder_board, 24)
encoder = rotaryio.IncrementalEncoder(encoder_board)

# Joystick Setup
joystick = qwiic_joystick.QwiicJoystick()
if not joystick.connected:
    print("Joystick not connected!", file=sys.stderr)
    sys.exit(1)
joystick.begin()

# ==================== GAME CONSTANTS ====================

SCREEN_WIDTH = 135
SCREEN_HEIGHT = 240
CELL_SIZE = 6
GRID_WIDTH = SCREEN_WIDTH // CELL_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // CELL_SIZE

# Colors
COLOR_BLACK = color565(0, 0, 0)
COLOR_WHITE = color565(255, 255, 255)
COLOR_GREEN = color565(0, 255, 0)
COLOR_RED = color565(255, 0, 0)
COLOR_BLUE = color565(0, 100, 255)
COLOR_YELLOW = color565(255, 255, 0)
COLOR_GRAY = color565(128, 128, 128)

# Joystick thresholds
JOY_CENTER = 512
JOY_THRESHOLD = 200

# ==================== HELPER FUNCTIONS ====================

def draw_cell(x, y, color):
    """Draw a single cell on the grid"""
    px = x * CELL_SIZE
    py = y * CELL_SIZE
    for i in range(CELL_SIZE):
        for j in range(CELL_SIZE):
            if px + i < SCREEN_WIDTH and py + j < SCREEN_HEIGHT:
                display.pixel(px + i, py + j, color)

def draw_char(char, x, y, color):
    """Draw a simple 5x7 character"""
    # Simple bitmap font for essential characters
    font = {
        'A': [0x7E, 0x11, 0x11, 0x11, 0x7E],
        'B': [0x7F, 0x49, 0x49, 0x49, 0x36],
        'C': [0x3E, 0x41, 0x41, 0x41, 0x22],
        'D': [0x7F, 0x41, 0x41, 0x22, 0x1C],
        'E': [0x7F, 0x49, 0x49, 0x49, 0x41],
        'F': [0x7F, 0x09, 0x09, 0x09, 0x01],
        'G': [0x3E, 0x41, 0x49, 0x49, 0x7A],
        'H': [0x7F, 0x08, 0x08, 0x08, 0x7F],
        'I': [0x00, 0x41, 0x7F, 0x41, 0x00],
        'L': [0x7F, 0x40, 0x40, 0x40, 0x40],
        'M': [0x7F, 0x02, 0x0C, 0x02, 0x7F],
        'N': [0x7F, 0x04, 0x08, 0x10, 0x7F],
        'O': [0x3E, 0x41, 0x41, 0x41, 0x3E],
        'Q': [0x3E, 0x41, 0x51, 0x21, 0x5E],
        'R': [0x7F, 0x09, 0x19, 0x29, 0x46],
        'S': [0x46, 0x49, 0x49, 0x49, 0x31],
        'T': [0x01, 0x01, 0x7F, 0x01, 0x01],
        'U': [0x3F, 0x40, 0x40, 0x40, 0x3F],
        'Y': [0x07, 0x08, 0x70, 0x08, 0x07],
        ' ': [0x00, 0x00, 0x00, 0x00, 0x00],
    }
    
    if char in font:
        pattern = font[char]
        for col in range(5):
            byte = pattern[col]
            for row in range(7):
                if byte & (1 << row):
                    display.pixel(x + col, y + row, color)

def draw_text(text, x, y, color=COLOR_WHITE):
    """Draw text string"""
    for i, char in enumerate(text):
        draw_char(char, x + i * 6, y, color)

def get_joystick_direction():
    """Get direction from joystick"""
    x = joystick.horizontal
    y = joystick.vertical
    
    # Determine primary direction
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
        # Prevent 180-degree turns
        opposites = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}
        if new_direction and opposites[new_direction] != self.direction:
            self.direction = new_direction
    
    def check_collision(self):
        head_x, head_y = self.body[0]
        
        # Wall collision
        if head_x < 0 or head_x >= GRID_WIDTH or head_y < 0 or head_y >= GRID_HEIGHT:
            return True
        
        # Self collision
        if self.body[0] in self.body[1:]:
            return True
        
        return False
    
    def eat(self):
        self.grow_pending += 3

class Food:
    def __init__(self, snake):
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
        self.options = ['START GAME', 'DIFFICULTY', 'QUIT']
        self.selected = 0
        self.last_encoder_pos = 0
        self.difficulty_level = 1  # 0=Easy, 1=Normal, 2=Hard
        self.difficulty_names = ['EASY', 'NORMAL', 'HARD']
    
    def update(self):
        # Read encoder position
        pos = -encoder.position
        if pos != self.last_encoder_pos:
            diff = pos - self.last_encoder_pos
            self.selected = (self.selected + diff) % len(self.options)
            self.last_encoder_pos = pos
            return True
        return False
    
    def select(self):
        return self.options[self.selected]
    
    def draw(self):
        display.fill(COLOR_BLACK)
        
        # Title
        draw_text("SNAKE", 45, 10, COLOR_GREEN)
        
        # Menu options
        for i, option in enumerate(self.options):
            y_pos = 50 + i * 35
            color = COLOR_YELLOW if i == self.selected else COLOR_WHITE
            
            # Draw selection indicator (arrow)
            if i == self.selected:
                # Simple arrow: >
                for dy in range(-2, 3):
                    display.pixel(10, y_pos + 10 + dy, COLOR_YELLOW)
                display.pixel(11, y_pos + 9, COLOR_YELLOW)
                display.pixel(11, y_pos + 11, COLOR_YELLOW)
                display.pixel(12, y_pos + 8, COLOR_YELLOW)
                display.pixel(12, y_pos + 12, COLOR_YELLOW)
            
            # Draw option text
            draw_text(option, 20, y_pos + 7, color)
            
            # Show difficulty level for difficulty option
            if option == 'DIFFICULTY':
                difficulty_text = self.difficulty_names[self.difficulty_level]
                draw_text(difficulty_text, 20, y_pos + 18, 
                         [COLOR_GREEN, COLOR_YELLOW, COLOR_RED][self.difficulty_level])

# ==================== MAIN GAME ====================

def draw_game(snake, food, score):
    display.fill(COLOR_BLACK)
    
    # Draw snake
    for i, (x, y) in enumerate(snake.body):
        if i == 0:
            draw_cell(x, y, COLOR_GREEN)  # Head
        else:
            draw_cell(x, y, COLOR_BLUE)
    
    # Draw food
    draw_cell(food.position[0], food.position[1], COLOR_RED)
    
    # Draw score bar at top
    for x in range(min(score * 5, SCREEN_WIDTH)):
        for y in range(3):
            display.pixel(x, y, COLOR_YELLOW)

def game_loop(difficulty):
    snake = Snake()
    food = Food(snake)
    score = 0
    
    # Speed based on difficulty
    speeds = [0.15, 0.10, 0.07]  # Easy, Normal, Hard
    game_speed = speeds[difficulty]
    
    last_move_time = time.time()
    
    while True:
        current_time = time.time()
        
        # Check encoder button for pause/quit
        if not encoder_button.value:
            time.sleep(0.2)  # Debounce
            if not encoder_button.value:  # Still pressed
                return score  # Return to menu
        
        # Get joystick input
        direction = get_joystick_direction()
        snake.change_direction(direction)
        
        # Move snake at fixed intervals
        if current_time - last_move_time >= game_speed:
            snake.move()
            last_move_time = current_time
            
            # Check collision
            if snake.check_collision():
                # Game over animation
                for _ in range(3):
                    display.fill(COLOR_RED)
                    time.sleep(0.2)
                    draw_game(snake, food, score)
                    time.sleep(0.2)
                return score
            
            # Check food
            if snake.body[0] == food.position:
                snake.eat()
                score += 1
                food.spawn(snake)
        
        draw_game(snake, food, score)
        time.sleep(0.01)

# ==================== MAIN ====================

def main():
    menu = Menu()
    
    while True:
        # Menu loop
        menu.draw()
        last_button_state = encoder_button.value
        
        while True:
            if menu.update():
                menu.draw()
            
            # Check encoder button press
            if not encoder_button.value and last_button_state:
                time.sleep(0.2)  # Debounce
                selection = menu.select()
                
                if selection == 'START GAME':
                    score = game_loop(menu.difficulty_level)
                    # Show score briefly
                    display.fill(COLOR_BLACK)
                    for x in range(min(score * 5, SCREEN_WIDTH)):
                        for y in range(60, 70):
                            display.pixel(x, y, COLOR_GREEN)
                    time.sleep(2)
                    break
                
                elif selection == 'DIFFICULTY':
                    menu.difficulty_level = (menu.difficulty_level + 1) % 3
                    menu.draw()
                
                elif selection == 'QUIT':
                    display.fill(COLOR_BLACK)
                    backlight.value = False
                    sys.exit(0)
            
            last_button_state = encoder_button.value
            time.sleep(0.01)

if __name__ == '__main__':
    try:
        print("Snake Game Starting...")
        print("Joystick: Control snake direction")
        print("Encoder: Navigate menu, press to select/pause")
        main()
    except KeyboardInterrupt:
        display.fill(COLOR_BLACK)
        backlight.value = False
        print("\nGame ended")
        sys.exit(0)
