#!/usr/bin/env python3
"""
Run this script on the Raspberry Pi to use the Pi's microphone for voice control.
This runs independently from the web interface.

Install dependencies first:
    pip3 install SpeechRecognition pyaudio requests
    sudo apt-get install portaudio19-dev python3-pyaudio
"""

import speech_recognition as sr
import requests
import time

# Configuration
FLASK_URL = "http://localhost:5000"  # Your Flask server
TRIGGER_WORDS = ["play", "start", "run", "activate", "show"]

def listen_for_commands():
    """Continuously listen for voice commands using Pi's microphone"""
    
    # Initialize recognizer
    recognizer = sr.Recognizer()
    
    # Adjust for ambient noise
    with sr.Microphone() as source:
        print("[*] Calibrating microphone for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
        print("[OK] Microphone ready! Listening for commands...")
        print("[INFO] Say: 'Play [scene name]' or just '[scene name]'")
        print("-" * 50)
    
    while True:
        try:
            with sr.Microphone() as source:
                # Listen for audio
                print("[LISTENING...]")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
                try:
                    # Convert speech to text using Google Speech Recognition
                    text = recognizer.recognize_google(audio).lower()
                    print(f"[HEARD] '{text}'")
                    
                    # Process the command
                    process_voice_command(text)
                    
                except sr.UnknownValueError:
                    print("[?] Could not understand audio")
                except sr.RequestError as e:
                    print(f"[ERROR] Could not request results; {e}")
                    
        except sr.WaitTimeoutError:
            # Timeout is normal, just continue listening
            pass
        except KeyboardInterrupt:
            print("\n[STOP] Stopping voice control...")
            break
        except Exception as e:
            print(f"[WARNING] Error: {e}")
            time.sleep(1)

def process_voice_command(text):
    """Extract scene name and send to Flask server"""
    
    # Remove trigger words to get scene name
    scene_name = text
    for trigger in TRIGGER_WORDS:
        if trigger in text:
            scene_name = text.replace(trigger, "").strip()
            break
    
    if not scene_name:
        print("[WARNING] No scene name detected")
        return
    
    print(f"[STARTING] Attempting to start scene: '{scene_name}'")
    
    # Send request to Flask server
    try:
        response = requests.post(
            f"{FLASK_URL}/api/start-by-name/{scene_name}",
            timeout=5
        )
        
        result = response.json()
        
        if result.get('status') == 'success':
            print(f"[SUCCESS] {result.get('message')}")
        else:
            print(f"[FAILED] {result.get('message')}")
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to Flask server. Is it running?")
    except Exception as e:
        print(f"[ERROR] Error starting scene: {e}")

def test_microphone():
    """Test if microphone is working"""
    print("[*] Testing microphone...")
    recognizer = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            print("[OK] Microphone detected!")
            print("[INFO] Available microphones:")
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                print(f"  [{index}] {name}")
            return True
    except Exception as e:
        print(f"[ERROR] Microphone error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("PI MICROPHONE VOICE CONTROL")
    print("=" * 50)
    
    # Test microphone first
    if test_microphone():
        print("\n" + "=" * 50)
        input("Press ENTER to start listening for commands...")
        listen_for_commands()
    else:
        print("\n[ERROR] Please fix microphone issues and try again")
        print("\nTroubleshooting:")
        print("  1. Check if mic is connected: arecord -l")
        print("  2. Install dependencies: sudo apt-get install portaudio19-dev")
        print("  3. Test mic: arecord -d 3 test.wav && aplay test.wav")