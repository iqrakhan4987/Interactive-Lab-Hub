import time
import sys
import serial
import board
import busio
import adafruit_mpr121

# --- CONFIGURATION ---
# Check if your Arduino is ttyACM0 or ttyUSB0
ARDUINO_PORT = '/dev/ttyACM0' 
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

# --- SETUP: TOUCH SENSOR (MPR121) ---
try:
    i2c = board.I2C()
    # Default I2C address for MPR121 is 0x5A
    mpr121 = adafruit_mpr121.MPR121(i2c, address=0x5A)
    print("MPR121 Touch Sensor connected!")
except Exception as e:
    print(f"Error finding MPR121: {e}")
    print("Check wiring: 3.3V->Vin, Gnd->Gnd, SDA->SDA, SCL->SCL")
    sys.exit()

# --- MIXING VARIABLES ---
red_drops = 0
green_drops = 0
blue_drops = 0

# --- HELPER FUNCTIONS ---
def send_color_command(r, g, b):
    # Sends "C,Red,Green,Blue\n" to trigger Mode B on the Universal Arduino Driver
    cmd = f"C,{int(r)},{int(g)},{int(b)}\n"
    ser.write(cmd.encode('utf-8'))

def calculate_and_update():
    total_drops = red_drops + green_drops + blue_drops
    
    if total_drops == 0:
        print("Palette Empty (Lights OFF)             ", end='\r')
        send_color_command(0, 0, 0)
        return

    # Calculate percentage of each color vs total drops
    # Then scale to 0-255 brightness
    r_val = (red_drops / total_drops) * 255
    g_val = (green_drops / total_drops) * 255
    b_val = (blue_drops / total_drops) * 255
    
    print(f"Mix: R:{red_drops} G:{green_drops} B:{blue_drops} -> RGB({int(r_val)}, {int(g_val)}, {int(b_val)})    ", end='\r')
    send_color_command(r_val, g_val, b_val)

# --- MAIN LOOP ---
print("\n--- COLOR MIXER STARTED ---")
print("Lead 0: Add RED drop")
print("Lead 1: Add GREEN drop")
print("Lead 2: Add BLUE drop")
print("Lead 11: RESET (Clean Palette)")
print("Press Ctrl+C to exit.")
print("---------------------------")

# We track the 'last' state to detect distinct taps (rising edge)
# otherwise holding the wire would add 1000 drops a second.
last_touched = mpr121.touched()

try:
    while True:
        current_touched = mpr121.touched()
        
        # Check the first 12 electrodes
        for i in range(12):
            # Check if pin 'i' is currently touched
            pin_is_touched = (current_touched >> i) & 1
            # Check if pin 'i' was touched in the previous loop
            pin_was_touched = (last_touched >> i) & 1
            
            # If it IS touched now, but WASN'T before -> That's a new Tap!
            if pin_is_touched and not pin_was_touched:
                if i == 0:
                    red_drops += 1
                    print("\n + RED drop added!   ")
                elif i == 1:
                    green_drops += 1
                    print("\n + GREEN drop added! ")
                elif i == 2:
                    blue_drops += 1
                    print("\n + BLUE drop added!  ")
                elif i == 11:
                    print("\n * RESET * ")
                    red_drops = 0
                    green_drops = 0
                    blue_drops = 0
                
                # Update lights immediately after a tap
                calculate_and_update()

        # Save current state for the next loop
        last_touched = current_touched
        
        # Small delay to prevent CPU overload
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nExiting...")
    send_color_command(0, 0, 0)
    ser.close()