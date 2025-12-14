import serial
import time
import sys

# --- CONFIGURATION ---
# Try to auto-detect the port (ACM0 or USB0)
possible_ports = ['/dev/ttyACM0', '/dev/ttyUSB0', '/dev/ttyACM1', '/dev/ttyUSB1']
ser = None

print("Scanning for Arduino...")
for port in possible_ports:
    try:
        # Open serial connection at 9600 baud (must match Arduino code)
        ser = serial.Serial(port, 9600, timeout=1)
        ser.reset_input_buffer()
        print(f"Connected to Arduino on {port}")
        break 
    except:
        pass

if ser is None:
    print("ERROR: Arduino not found!")
    print("Check: Is the USB cable plugged in?")
    sys.exit()

# Wait for Arduino to reboot after connection (standard behavior)
print("Waiting for Arduino to reset...")
time.sleep(2)

def send_color(r, g, b):
    """Sends R, G, B command to Arduino"""
    # Format: "R, G, B\n" (e.g., "255, 0, 0\n")
    command = f"{int(r)},{int(g)},{int(b)}\n"
    
    # Encode string to bytes and send
    ser.write(command.encode('utf-8'))
    print(f"Sent: {command.strip()}")

# --- TEST PATTERN ---
try:
    print("\n--- STARTING TEST LOOP ---")
    print("Press Ctrl+C to exit.\n")
    
    while True:
        # RED
        print("Testing RED...")
        send_color(255, 0, 0)
        time.sleep(1)

        # GREEN
        print("Testing GREEN...")
        send_color(0, 255, 0)
        time.sleep(1)

        # BLUE
        print("Testing BLUE...")
        send_color(0, 0, 255)
        time.sleep(1)

        # WHITE (Max Brightness)
        print("Testing WHITE...")
        send_color(255, 255, 255)
        time.sleep(1)

        # OFF
        print("Turning OFF...")
        send_color(0, 0, 0)
        time.sleep(1)

except KeyboardInterrupt:
    print("\nExiting...")
    send_color(0, 0, 0) # Ensure lights are off
    ser.close()