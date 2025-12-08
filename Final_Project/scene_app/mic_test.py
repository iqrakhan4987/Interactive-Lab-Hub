import speech_recognition as sr
import time

def check_microphone():
    print("------------------------------------------------")
    print("   MICROPHONE DIAGNOSTIC TOOL")
    print("------------------------------------------------")
    
    # 1. Check if PyAudio detects devices
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        print(f"[System] Found {numdevices} audio devices.")
        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                print(f"  - Device {i}: {p.get_device_info_by_host_api_device_index(0, i).get('name')}")
        p.terminate()
    except ImportError:
        print("[Error] PyAudio not installed. Run: pip install pyaudio")
        return
    except Exception as e:
        print(f"[Warning] Could not list devices: {e}")

    # 2. Initialize Speech Recognition
    r = sr.Recognizer()
    
    # Optional: Adjust sensitivity
    r.energy_threshold = 300 
    r.dynamic_energy_threshold = True
    
    print("\n[Init] Adjusting for background noise... (Please stay quiet)")
    
    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=2)
            print(f"[Init] Ready! Threshold set to {r.energy_threshold}")
            print("------------------------------------------------")
            print(" SPEAK NOW (Say 'Hello' or 'Lumos')")
            print(" Press Ctrl+C to exit")
            print("------------------------------------------------")
            
            while True:
                try:
                    print(" Listening...", end='\r', flush=True)
                    # Listen with a timeout so it doesn't hang forever
                    audio = r.listen(source, timeout=5, phrase_time_limit=5)
                    
                    print(" Processing...", end='\r', flush=True)
                    # Send to Google
                    text = r.recognize_google(audio)
                    print(f" > HEARD: '{text}'              ")
                    
                except sr.WaitTimeoutError:
                    pass # Just keep listening
                except sr.UnknownValueError:
                    print(" > (Noise detected, but could not understand words)")
                except sr.RequestError as e:
                    print(f" > [Network Error] Could not reach Google: {e}")
                    
    except KeyboardInterrupt:
        print("\n[Exit] Test stopped by user.")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        print("Tip: Check if your mic is plugged in or if another program is using it.")

if __name__ == "__main__":
    check_microphone()