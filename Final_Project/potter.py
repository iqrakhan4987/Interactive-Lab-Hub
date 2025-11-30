import time
import sys
import serial
import speech_recognition as sr

# --- CONFIGURATION ---
ARDUINO_PORT = '/dev/ttyACM0' # Change if needed (e.g. ttyUSB0)
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

# --- HELPER FUNCTION ---
def set_lights(brightness):
    # We send position 0 (rainbow start) and the requested brightness
    # Format: "Position,Brightness\n"
    cmd = f"0,{int(brightness)}\n"
    ser.write(cmd.encode('utf-8'))
    print(f"Lights set to brightness: {brightness}")

# --- VOICE SETUP ---
recognizer = sr.Recognizer()
mic = sr.Microphone()

print("Adjusting for ambient noise... (Please stay quiet)")
with mic as source:
    recognizer.adjust_for_ambient_noise(source, duration=2)
    recognizer.dynamic_energy_threshold = True

print("\n--- SPELL LISTENING MODE ---")
print("Say 'Lumos Maxima' to turn ON")
print("Say 'Nox' to turn OFF")
print("----------------------------")

# --- MAIN LOOP ---
try:
    while True:
        print("Listening for spells...", end='\r')
        
        with mic as source:
            try:
                # Listen for audio (times out after 5 seconds of silence)
                # phrase_time_limit prevents it from getting stuck listening to noise
                audio = recognizer.listen(source, timeout=5.0, phrase_time_limit=5.0)
                
                # Recognize speech
                command = recognizer.recognize_google(audio).lower()
                print(f"\nHeard: '{command}'")
                
                # --- SPELL LOGIC ---
                if "lumos" in command:
                    print("*** SPELL CAST: LUMOS MAXIMA! ***")
                    set_lights(255) # Max Brightness
                    
                elif "nox" in command or "knocks" in command: 
                    print("*** SPELL CAST: NOX! ***")
                    set_lights(0)   # Off
                    
                else:
                    print("Spell failed (Unknown command).")
                    
            except sr.WaitTimeoutError:
                pass # No speech detected, keep listening
            except sr.UnknownValueError:
                # print("\n(Could not understand audio)") # Uncomment to debug
                pass
            except sr.RequestError as e:
                print(f"\nNetwork Error: {e}")

except KeyboardInterrupt:
    print("\nExiting...")
    set_lights(0)
    ser.close()