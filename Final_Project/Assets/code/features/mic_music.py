import time
import sys
import serial
import sounddevice as sd
import numpy as np

# --- CONFIGURATION ---
ARDUINO_PORT = '/dev/ttyACM0' # Change if needed
BAUD_RATE = 9600

# SETTINGS
MIN_SPEED = 0.5    # How fast it spins when silent
MAX_SPEED = 50.0   # Maximum spin speed (prevent seizures)
SENSITIVITY = 20.0 # Increase this if the mic is too quiet

# --- SETUP: ARDUINO ---
try:
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.1)
    ser.reset_input_buffer()
    time.sleep(2)
    print(f"Connected to Arduino on {ARDUINO_PORT}")
except Exception as e:
    print(f"Error connecting to Arduino: {e}")
    sys.exit()

# --- HELPER FUNCTIONS ---
def send_state(position, brightness):
    # Sends "Position,Brightness\n" to Arduino
    try:
        cmd = f"{int(position)},{int(brightness)}\n"
        ser.write(cmd.encode('utf-8'))
    except:
        pass # Ignore errors if serial buffer is full

# --- MAIN LOOP ---
print("\n--- AUDIO RAINBOW STARTED ---")
print("Make some noise to spin the rainbow!")
print("Press Ctrl+C to exit.")

rainbow_offset = 0
current_speed = MIN_SPEED

# The Audio Callback runs in a separate thread whenever data arrives
def audio_callback(indata, frames, time_info, status):
    global rainbow_offset, current_speed
    
    # 1. Calculate Volume (Root Mean Square)
    # We use numpy to get the magnitude of the sound waves
    volume = np.linalg.norm(indata) * SENSITIVITY
    
    # 2. Map Volume to Speed
    # Quiet (0 volume) -> MIN_SPEED
    # Loud -> Higher Speed
    target_speed = MIN_SPEED + volume
    
    # Cap the speed so it doesn't go crazy
    if target_speed > MAX_SPEED: 
        target_speed = MAX_SPEED
    
    # Smooth the speed change (Optional, makes it look less glitchy)
    current_speed = (current_speed * 0.8) + (target_speed * 0.2)
    
    # 3. Advance the Rainbow
    # We add the speed to the current position
    rainbow_offset = (rainbow_offset + current_speed) % 255
    
    # 4. Send to Arduino
    # We keep brightness maxed (255) so colors are vivid
    send_state(rainbow_offset, 255)

# --- START LISTENING ---
try:
    # Open the microphone stream
    # blocksize=0 allows the system to choose the optimal buffer size
    with sd.InputStream(callback=audio_callback, blocksize=0, channels=1):
        while True:
            # The work happens in the callback background thread
            # We just sleep here to keep the script alive
            time.sleep(0.1)

except KeyboardInterrupt:
    print("\nExiting...")
    send_state(0, 0) # Turn off lights
    ser.close()
except Exception as e:
    print(f"\nAudio Error: {e}")
    print("Try installing portaudio: sudo apt-get install libportaudio2")