import queue
import sounddevice as sd
import vosk
import json
import subprocess
import shutil
import threading
import requests
import time
import digitalio
import board
from PIL import Image, ImageDraw
import adafruit_rgb_display.st7789 as st7789

# Configuration
MODEL_PATH = "model"
OLLAMA_URL = "http://localhost:11434/api/generate"

# Display Configuration (from your working code)
cs_pin = digitalio.DigitalInOut(board.D5) 
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None
BAUDRATE = 64000000

spi = board.SPI()

disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
)

# Display dimensions
height = disp.width
width = disp.height
rotation = 90

# Backlight
backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

# Button setup
button_pin = digitalio.DigitalInOut(board.D23)
button_pin.direction = digitalio.Direction.INPUT
button_pin.pull = digitalio.Pull.UP

# Conversation memory
conversation_memory = {
    "is_speaking": False,
    "is_listening": False,
    "conversation_history": [],
    "button_pressed": False
}

def draw_face(state="idle"):
    """Draw animated face on display"""
    image = Image.new("RGB", (width, height), color=(20, 20, 40))
    draw = ImageDraw.Draw(image)
    
    face_color = (255, 220, 180)
    eye_color = (50, 50, 50)
    
    face_radius = 50
    face_center_x = width // 2
    face_center_y = height // 2
    
    # Face circle
    draw.ellipse(
        [face_center_x - face_radius, face_center_y - face_radius,
         face_center_x + face_radius, face_center_y + face_radius],
        fill=face_color
    )
    
    # Eyes
    eye_y = face_center_y - 15
    left_eye_x = face_center_x - 20
    right_eye_x = face_center_x + 20
    eye_radius = 5
    
    if state == "thinking":
        # Squinting eyes
        draw.arc([left_eye_x - eye_radius, eye_y - 3, left_eye_x + eye_radius, eye_y + 3],
                 start=0, end=180, fill=eye_color, width=3)
        draw.arc([right_eye_x - eye_radius, eye_y - 3, right_eye_x + eye_radius, eye_y + 3],
                 start=0, end=180, fill=eye_color, width=3)
    else:
        # Normal eyes
        draw.ellipse([left_eye_x - eye_radius, eye_y - eye_radius,
                     left_eye_x + eye_radius, eye_y + eye_radius], fill=eye_color)
        draw.ellipse([right_eye_x - eye_radius, eye_y - eye_radius,
                     right_eye_x + eye_radius, eye_y + eye_radius], fill=eye_color)
    
    # Mouth
    mouth_y = face_center_y + 15
    
    if state == "speaking":
        # Open mouth
        draw.ellipse([face_center_x - 15, mouth_y - 10,
                     face_center_x + 15, mouth_y + 10], fill=(80, 40, 40))
    elif state == "listening":
        # Small circle
        draw.ellipse([face_center_x - 8, mouth_y - 8,
                     face_center_x + 8, mouth_y + 8], fill=(80, 40, 40))
    elif state == "thinking":
        # Wavy line
        draw.arc([face_center_x - 20, mouth_y - 5,
                 face_center_x + 20, mouth_y + 5],
                start=180, end=360, fill=eye_color, width=3)
    else:  # idle - smile
        draw.arc([face_center_x - 20, mouth_y - 10,
                 face_center_x + 20, mouth_y + 10],
                start=0, end=180, fill=eye_color, width=3)
    
    disp.image(image, rotation)

def animate_speaking():
    """Animate mouth while speaking"""
    while conversation_memory["is_speaking"]:
        draw_face("speaking")
        time.sleep(0.15)
        # Alternate mouth size
        image = Image.new("RGB", (width, height), color=(20, 20, 40))
        draw = ImageDraw.Draw(image)
        face_color = (255, 220, 180)
        eye_color = (50, 50, 50)
        face_radius = 50
        face_center_x = width // 2
        face_center_y = height // 2
        
        # Face
        draw.ellipse([face_center_x - face_radius, face_center_y - face_radius,
                     face_center_x + face_radius, face_center_y + face_radius], fill=face_color)
        # Eyes
        eye_y = face_center_y - 15
        left_eye_x = face_center_x - 20
        right_eye_x = face_center_x + 20
        eye_radius = 5
        draw.ellipse([left_eye_x - eye_radius, eye_y - eye_radius,
                     left_eye_x + eye_radius, eye_y + eye_radius], fill=eye_color)
        draw.ellipse([right_eye_x - eye_radius, eye_y - eye_radius,
                     right_eye_x + eye_radius, eye_y + eye_radius], fill=eye_color)
        # Smaller mouth
        mouth_y = face_center_y + 15
        draw.ellipse([face_center_x - 10, mouth_y - 5,
                     face_center_x + 10, mouth_y + 5], fill=(80, 40, 40))
        disp.image(image, rotation)
        time.sleep(0.15)
    
    draw_face("idle")

def get_ai_response(user_message):
    """Get response from TinyLlama via Ollama"""
    try:
        conversation_memory["conversation_history"].append(user_message)
        
        prompt = "You are a supportive friend. Keep responses very brief (1-2 sentences).\n\n"
        prompt += f"Friend: {user_message}\nYou:"
        
        payload = {
            "model": "tinyllama",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 50,
                "stop": ["\nFriend:", "Friend:", "\nYou:", "\n\n"],
                "repeat_penalty": 1.2
            }
        }
        
        print("[DEBUG] Getting AI response...")
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get("response", "").strip()
            
            # Clean up response
            ai_response = ai_response.replace("You:", "").replace("Friend:", "").strip()
            ai_response = ai_response.replace("Me:", "").replace("Mate:", "").strip()
            ai_response = ai_response.replace("Responding:", "").replace("Sure thing!", "").strip()
            ai_response = " ".join(ai_response.split())
            
            # Take first 2 sentences
            sentences = []
            temp = ai_response.replace("! ", "!|").replace("? ", "?|").replace(". ", ".|")
            for sent in temp.split("|"):
                sent = sent.strip()
                if sent and len(sent) > 10:
                    sentences.append(sent)
                if len(sentences) >= 2:
                    break
            
            if sentences:
                ai_response = " ".join(sentences)
                if ai_response[-1] not in ".!?":
                    ai_response += "."
            
            if ai_response and len(ai_response) > 10:
                conversation_memory["conversation_history"].append(ai_response)
                return ai_response
            else:
                fallbacks = ["Tell me more about that.", "How does that make you feel?",
                           "I'm listening. Go on.", "What else is on your mind?"]
                return fallbacks[len(conversation_memory["conversation_history"]) % 4]
        
        return "Can you say that again?"
    except Exception as e:
        print(f"[DEBUG] Error: {type(e).__name__}")
        return "Could you repeat that?"


def speak(text):
    """Text-to-speech with animated face"""
    conversation_memory["is_speaking"] = True
    
    # Start animation
    anim_thread = threading.Thread(target=animate_speaking, daemon=True)
    anim_thread.start()
    
    piper_path = shutil.which("piper")
    if piper_path:
        cmd = [piper_path, "--model", "piper_models/en_US-lessac-medium/en_US-lessac-medium.onnx", "--output-raw"]
        try:
            p1 = subprocess.Popen(["echo", text], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(cmd, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            p3 = subprocess.Popen(["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
                                stdin=p2.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            p3.wait()  # ← This was there but...
        except:
            pass
    
    conversation_memory["is_speaking"] = False  # ← This needs to be OUTSIDE the if/try block!
    time.sleep(0.3)

# Vosk setup
print("Loading speech recognition model...")
vosk_model = vosk.Model(MODEL_PATH)
rec = vosk.KaldiRecognizer(vosk_model, 16000)
q = queue.Queue()

def callback(indata, frames, time_info, status):
    if conversation_memory["is_listening"] and not conversation_memory["is_speaking"]:
        q.put(bytes(indata))

print("\n" + "="*60)
print("AI VOICE ASSISTANT with Mini PiTFT")
print("="*60)
print("\nPress button to talk!")
print("Say 'goodbye' to exit")
print("="*60 + "\n")

# Initial greeting
draw_face("idle")
time.sleep(1)
initial_greeting = "Hi! How are you feeling today?"
print(f"Assistant: {initial_greeting}\n")
speak(initial_greeting)

with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16', channels=1, callback=callback):
    try:
        while True:
            # Wait for button press
            while button_pin.value:  # Wait while button NOT pressed
                time.sleep(0.01)
            time.sleep(0.05)  # Debounce
            while not button_pin.value:  # Wait for release
                time.sleep(0.01)
            
            print("\nRECORDING... (Press button when done)")
            draw_face("listening")
            conversation_memory["is_listening"] = True
            rec = vosk.KaldiRecognizer(vosk_model, 16000)
            
            accumulated_text = ""
            start_time = time.time()
            
            # Record until button pressed again or timeout
            while time.time() - start_time < 30:  # 30 sec timeout
                # Check for button press
                if not button_pin.value:  # Button pressed
                    time.sleep(0.05)  # Debounce
                    if not button_pin.value:
                        while not button_pin.value:  # Wait for release
                            time.sleep(0.01)
                        break
                
                try:
                    data = q.get(timeout=0.1)
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "")
                        if text:
                            accumulated_text += " " + text
                except:
                    continue
            
            final_result = json.loads(rec.FinalResult())
            final_text = final_result.get("text", "")
            if final_text:
                accumulated_text += " " + final_text
            
            conversation_memory["is_listening"] = False
            accumulated_text = accumulated_text.strip()
            
            if not accumulated_text or len(accumulated_text) < 2:
                print("(No speech detected)\n")
                draw_face("idle")
                continue
            
            print(f"\nYou: {accumulated_text}\n")
            
            if any(word in accumulated_text.lower() for word in ["bye", "goodbye", "exit", "quit"]):
                response = "Take care! It was nice talking with you."
                print(f"Assistant: {response}\n")
                speak(response)
                break
            
            print("[Thinking...]")
            draw_face("thinking")
            response = get_ai_response(accumulated_text)
            print(f"Assistant: {response}\n")
            speak(response)
    
    except KeyboardInterrupt:
        print("\nExiting...")
        draw_face("idle")
