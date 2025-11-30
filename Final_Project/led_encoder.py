import time
import sys
import serial
import board
from adafruit_seesaw import seesaw, rotaryio

# --- CONFIGURATION ---
ARDUINO_PORT = '/dev/ttyACM0' # Change to ttyUSB0 if needed
BAUD_RATE = 9600

# --- SETUP: ARDUINO ---
try:
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.1)
    ser.reset_input_buffer()
    time.sleep(2)
    print(f"Connected to Arduino on {ARDUINO_PORT}")
except Exception as e:
    print(f"Error connecting to Arduino: {e}")
    sys.exit()

# --- SETUP: ROTARY ENCODER (Address 0x36) ---
try:
    # Initialize I2C
    i2c = board.I2C()
    seesaw_device = seesaw.Seesaw(i2c, addr=0x36)
    
    # Verify Product ID (4991 is the Adafruit QT Encoder)
    seesaw_product = (seesaw_device.get_version() >> 16) & 0xFFFF
    print("Found product {}".format(seesaw_product))
    if seesaw_product != 4991:
        print("Warning: Chip ID mismatch. Expected 4991.")

    # Configure Encoder
    encoder = rotaryio.IncrementalEncoder(seesaw_device)
    
    print("Adafruit Rotary Encoder initialized!")

except Exception as e:
    print(f"CRITICAL ERROR: Knob not found at 0x36.")
    print(f"Details: {e}")
    sys.exit()

# --- HELPER FUNCTIONS ---
def send_color(r, g, b):
    # Sends "R,G,B\n" to Arduino
    cmd = f"{int(r)},{int(g)},{int(b)}\n"
    ser.write(cmd.encode('utf-8'))

def constrain(val, min_val, max_val):
    return max(min_val, min(val, max_val))

# --- MAIN LOOP ---
print("\n--- ROTARY CONTROL STARTED ---")
print("Turn Knob -> Change Brightness (White Light)")
print("Press Ctrl+C to exit.")

# State variables
last_position = 0
brightness = 255   # 0 to 255

try:
    # Initialize position
    last_position = -encoder.position

    while True:
        # 1. Read Inputs
        current_position = -encoder.position
        
        # 2. Did the knob move?
        if current_position != last_position:
            change = current_position - last_position
            
            # 3. LOGIC: Change Brightness
            # We multiply change by 5 to scroll faster
            brightness = constrain(brightness + (change * 5), 0, 255)
            print(f"Brightness: {brightness}   ", end='\r')
            
            last_position = current_position

            # 4. SEND TO ARDUINO (White Light)
            # Sends (Brightness, Brightness, Brightness) for white
            send_color(brightness, brightness, brightness)
            
        time.sleep(0.01) # Short delay

except KeyboardInterrupt:
    print("\nExiting...")
    send_color(0, 0, 0)
    ser.close()