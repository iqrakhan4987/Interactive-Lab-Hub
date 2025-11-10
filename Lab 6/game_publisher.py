#!/usr/bin/env python3
"""
Joystick Publisher for Multiplayer Shooter Game
Reads joystick input and publishes to MQTT for game control
Each Pi is identified by MAC address
"""

import time
import paho.mqtt.client as mqtt
import json
import subprocess
import signal
import sys

# Try to import joystick libraries
try:
    import board
    import busio
    import adafruit_seesaw.seesaw
    from adafruit_seesaw.seesaw import Seesaw
    JOYSTICK_AVAILABLE = True
except ImportError:
    JOYSTICK_AVAILABLE = False
    print("Joystick libraries not available - using keyboard simulation")

# MQTT Configuration
MQTT_BROKER = 'farlab.infosci.cornell.edu'
MQTT_PORT = 1883
MQTT_TOPIC = 'IDD/shooter/joystick'
MQTT_USERNAME = 'idd'
MQTT_PASSWORD = 'device@theFarm'

# Publishing interval (seconds)
PUBLISH_INTERVAL = 0.05  # 20 updates per second

# Joystick calibration
JOYSTICK_CENTER = 512
JOYSTICK_DEADZONE = 50
JOYSTICK_MAX = 1023

def get_mac_address():
    """Get the MAC address of the primary network interface"""
    try:
        result = subprocess.run(['cat', '/sys/class/net/eth0/address'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        
        result = subprocess.run(['cat', '/sys/class/net/wlan0/address'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"Error getting MAC address: {e}")
    
    return f"sim_{int(time.time())}"

def setup_joystick():
    """Setup the joystick hardware"""
    if not JOYSTICK_AVAILABLE:
        print("Running in simulation mode - use keyboard controls")
        return None
    
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        seesaw = Seesaw(i2c, addr=0x49)
        
        # Configure joystick pins
        seesaw.pin_mode(2, seesaw.INPUT_PULLUP)  # Button
        seesaw.pin_mode(3, seesaw.INPUT_PULLUP)  # Select button (optional)
        
        print("[OK] Joystick initialized")
        return seesaw
    except Exception as e:
        print(f"Error setting up joystick: {e}")
        return None

def read_joystick(seesaw):
    """Read joystick position and button state"""
    if seesaw is None:
        # Simulation mode - return center position
        return 0, 0, False
    
    try:
        # Read analog values (0-1023)
        x_raw = seesaw.analog_read(14)  # X axis
        y_raw = seesaw.analog_read(15)  # Y axis
        
        # Read button (active LOW)
        button = not seesaw.digital_read(2)
        
        # Normalize to -1.0 to 1.0 with deadzone
        def normalize(value):
            centered = value - JOYSTICK_CENTER
            if abs(centered) < JOYSTICK_DEADZONE:
                return 0.0
            
            if centered > 0:
                return (centered - JOYSTICK_DEADZONE) / (JOYSTICK_MAX - JOYSTICK_CENTER - JOYSTICK_DEADZONE)
            else:
                return (centered + JOYSTICK_DEADZONE) / (JOYSTICK_CENTER - JOYSTICK_DEADZONE)
        
        x = normalize(x_raw)
        y = normalize(y_raw)
        
        # Clamp values
        x = max(-1.0, min(1.0, x))
        y = max(-1.0, min(1.0, y))
        
        return x, y, button
        
    except Exception as e:
        print(f"Error reading joystick: {e}")
        return 0, 0, False

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print(f"[OK] Connected to MQTT broker: {MQTT_BROKER}")
    else:
        print(f"[ERROR] Connection failed with code {rc}")

def main():
    print("=" * 50)
    print("  Multiplayer Shooter - Joystick Controller")
    print("=" * 50)
    
    # Get device identifier
    mac_address = get_mac_address()
    print(f"Device ID: {mac_address}")
    print(f"MQTT Topic: {MQTT_TOPIC}")
    print()
    
    # Setup joystick
    print("Initializing joystick...")
    seesaw = setup_joystick()
    
    if not JOYSTICK_AVAILABLE:
        print("\n[SIMULATION MODE]")
        print("Joystick not available. Publishing test data.")
        print("In real deployment, connect Adafruit Seesaw joystick.")
    
    # Setup MQTT client
    print("Connecting to MQTT broker...")
    client = mqtt.Client(f"shooter_controller_{mac_address}")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    
    try:
        client.connect(MQTT_BROKER, port=MQTT_PORT, keepalive=60)
        client.loop_start()
        time.sleep(2)
        
        if client.is_connected():
            print(f"[OK] MQTT connected and ready")
        else:
            print("[WARNING] MQTT connection pending...")
    except Exception as e:
        print(f"[ERROR] Failed to connect to MQTT broker: {e}")
        return
    
    # Graceful exit handler
    def signal_handler(signum, frame):
        print("\nShutting down gracefully...")
        client.loop_stop()
        client.disconnect()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("\n" + "=" * 50)
    print("Streaming joystick data to game...")
    print(f"Update frequency: {PUBLISH_INTERVAL}s ({1/PUBLISH_INTERVAL:.0f} Hz)")
    print("Press Ctrl+C to exit")
    print("=" * 50 + "\n")
    
    last_publish_time = 0
    
    # For simulation mode
    sim_angle = 0
    
    # Main loop
    while True:
        try:
            current_time = time.time()
            
            if current_time - last_publish_time >= PUBLISH_INTERVAL:
                # Read joystick
                x, y, button = read_joystick(seesaw)
                
                # In simulation mode, create circular motion
                if not JOYSTICK_AVAILABLE:
                    sim_angle += 0.05
                    x = 0.3 * (time.time() % 10) / 10 - 0.15  # Slow drift
                    y = 0.3 * ((time.time() + 5) % 10) / 10 - 0.15
                    button = (int(time.time()) % 5) == 0  # Shoot every 5 seconds
                
                # Create payload
                payload = {
                    'mac': mac_address,
                    'x': round(x, 3),
                    'y': round(y, 3),
                    'button': button,
                    'timestamp': int(current_time)
                }
                
                # Publish to MQTT
                mqtt_payload = json.dumps(payload)
                result = client.publish(MQTT_TOPIC, mqtt_payload)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    status = "🔴 SHOOT!" if button else "      "
                    print(f"[OK] X:{x:+.2f} Y:{y:+.2f} {status} | {mac_address[:17]}")
                else:
                    print(f"[ERROR] Publish failed: rc={result.rc}")
                    if not client.is_connected():
                        print("[ERROR] Reconnecting...")
                        try:
                            client.reconnect()
                        except Exception as e:
                            print(f"[ERROR] Reconnect failed: {e}")
                
                last_publish_time = current_time
            
            time.sleep(0.01)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(1)
    
    # Cleanup
    client.loop_stop()
    client.disconnect()
    print("\nDisconnected. Goodbye!")

if __name__ == '__main__':
    main()