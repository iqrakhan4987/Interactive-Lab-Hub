# hardware.py
import serial
import time
import sys

POSSIBLE_PORTS = [
    '/dev/ttyACM0', '/dev/ttyUSB0',
    '/dev/ttyACM1', '/dev/ttyUSB1',
]

BAUD_RATE = 9600

def init_serial():
    print("[NEOPIXEL] Scanning for Arduino...")
    ser = None
    for port in POSSIBLE_PORTS:
        try:
            ser = serial.Serial(port, BAUD_RATE, timeout=1)
            ser.reset_input_buffer()
            print(f"[NEOPIXEL] ✅ Connected to Arduino on {port}")
            break
        except Exception:
            pass

    if ser is None:
        print("[NEOPIXEL] ❌ ERROR: Arduino not found! Running UI-only.")
        return None

    # Give Arduino time to reboot
    print("[NEOPIXEL] Waiting for Arduino to reset...")
    time.sleep(2)

    # Turn LEDs off at startup
    try:
        ser.write(b"0,0,0\n")
        print("[NEOPIXEL] Sent 0,0,0")
    except Exception as e:
        print(f"[NEOPIXEL] ERROR during initial write: {e}")

    return ser

arduino = init_serial()

def send_color(r: int, g: int, b: int) -> None:
    """Send an RGB color to the Arduino as 'R,G,B\\n'."""
    cmd = f"{int(r)},{int(g)},{int(b)}\n"

    if arduino is None:
        print(f"[NEOPIXEL] (Simulated) {cmd.strip()}")
        return

    try:
        arduino.write(cmd.encode('utf-8'))
        print(f"[NEOPIXEL] Sent {cmd.strip()}")
    except Exception as e:
        print(f"[NEOPIXEL] ERROR sending color: {e}")
