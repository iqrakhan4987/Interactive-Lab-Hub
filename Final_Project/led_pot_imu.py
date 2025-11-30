import time
import sys
import serial
import board
import math
import qwiic
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
    i2c = board.I2C()
    seesaw_device = seesaw.Seesaw(i2c, addr=0x36)
    
    # Verify Product ID for Adafruit Rotary Encoder (4991)
    seesaw_product = (seesaw_device.get_version() >> 16) & 0xFFFF
    if seesaw_product != 4991:
        print("Warning: Knob Chip ID mismatch. Expected 4991.")

    encoder = rotaryio.IncrementalEncoder(seesaw_device)
    print("Adafruit Rotary Encoder initialized!")

except Exception as e:
    print(f"CRITICAL ERROR: Knob not found at 0x36.")
    print("Tip: Check your wiring or run 'i2cdetect -y 1'")
    sys.exit()

# --- SETUP: IMU (SparkFun Qwiic) ---
print("Scanning for Qwiic IMU...")
imu = qwiic.QwiicIcm20948()

if imu.connected == False:
    print("Warning: Qwiic IMU not found. Check wiring!")
else:
    imu.begin()
    print("Qwiic IMU connected.")

# --- HELPER FUNCTIONS ---
def send_state(position, brightness):
    # Sends "Position,Brightness\n" to Arduino
    # Position: 0-255 (Where the rainbow starts on the ring)
    # Brightness: 0-255 (How bright the LEDs are)
    cmd = f"{int(position)},{int(brightness)}\n"
    ser.write(cmd.encode('utf-8'))

def constrain(val, min_val, max_val):
    return max(min_val, min(val, max_val))

# --- MAIN LOOP ---
print("\n--- RAINBOW RING STARTED ---")
print("1. Turn Knob -> Change Brightness")
print("2. Move IMU  -> Spin + STROBE (Disco Mode)")
print("Press Ctrl+C to exit.")

last_position = 0
knob_brightness = 255
rainbow_offset = 0 # 0 to 255 (Represents rotation angle)

# Blink Variables
last_blink_time = time.time()
light_is_on = True

try:
    # Initialize position
    last_position = -encoder.position

    while True:
        # --- 1. READ KNOB (Target Brightness) ---
        current_position = -encoder.position
        if current_position != last_position:
            change = current_position - last_position
            # Multiply by 5 to make brightness change feel responsive
            knob_brightness = constrain(knob_brightness + (change * 5), 0, 255)
            last_position = current_position

        # --- 2. READ IMU (Rainbow Spin + Blink Speed) ---
        current_brightness = knob_brightness # Default to knob value
        
        if imu.connected:
            gx, gy, gz = imu.get_gyro()
            
            # Calculate speed of movement (magnitude)
            movement_speed = math.sqrt(gx**2 + gy**2 + gz**2)
            
            # A. SPIN LOGIC
            # Spin faster when moving
            spin_speed = 5.0 + (movement_speed * 5.0)
            if spin_speed > 200: spin_speed = 200
            rainbow_offset = (rainbow_offset + spin_speed) % 255
            
            # B. BLINK (STROBE) LOGIC
            # Only blink if moving reasonably fast (threshold > 50)
            if movement_speed > 50:
                # Calculate interval: Faster move = Lower interval (Faster blink)
                # 15.0 / speed is a tuning factor. 
                # If speed is 150 -> 0.1s interval (5 blinks/sec)
                blink_interval = 15.0 / movement_speed
                if blink_interval < 0.04: blink_interval = 0.04 # Max strobe limit
                
                # Check timer
                if (time.time() - last_blink_time) > blink_interval:
                    light_is_on = not light_is_on # Toggle state
                    last_blink_time = time.time()
                
                # If "Off" state, override brightness to 0
                if not light_is_on:
                    current_brightness = 0
            else:
                # If not shaking fast enough, keep solid
                light_is_on = True
                
        else:
            # Fallback if IMU missing
            rainbow_offset = (rainbow_offset + 5.0) % 255

        # --- 3. SEND TO ARDUINO ---
        # We send 'current_brightness' which might be 0 if blinking
        print(f"Bright: {current_brightness} | Speed: {int(movement_speed) if imu.connected else 0}   ", end='\r')
        
        send_state(rainbow_offset, current_brightness)
        
        time.sleep(0.02) 

except KeyboardInterrupt:
    print("\nExiting...")
    send_state(0, 0)
    ser.close()