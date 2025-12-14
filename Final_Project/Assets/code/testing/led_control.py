import serial
import time

# --- SETUP ---
# Try to connect to the Arduino. 
# It usually shows up as /dev/ttyACM0 or /dev/ttyUSB0
try:
    arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
except:
    try:
        arduino = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
    except:
        print("Error: Arduino not found. Is it plugged in?")
        exit()

# Give the Arduino 2 seconds to reboot after connection
print("Connecting to Arduino...")
time.sleep(2) 
print("Ready!")

def set_color(r, g, b):
    # Create a string like "255,0,0\n"
    command = f"{r},{g},{b}\n"
    arduino.write(command.encode('utf-8'))
    print(f"Sent Color: {r}, {g}, {b}")

# --- MAIN LOOP ---
try:
    while True:
        print("Enter a color format: R,G,B (e.g. 255,0,0) or 'exit'")
        user_input = input(">> ")
        
        if user_input.lower() == 'exit':
            set_color(0,0,0) # Turn off before leaving
            break
            
        try:
            # Parse the user input
            parts = user_input.split(',')
            if len(parts) == 3:
                r = int(parts[0])
                g = int(parts[1])
                b = int(parts[2])
                set_color(r, g, b)
            else:
                print("Invalid format. Use R,G,B")
        except ValueError:
            print("Please enter numbers only.")

except KeyboardInterrupt:
    print("\nExiting...")
    set_color(0,0,0)
    arduino.close()