import cv2 as cv
import requests
import base64
import threading
import queue
import time
import json
import os
from teachable_machine_lite import TeachableMachineLite

# --- Teachable Machine (TM) Configuration ---
TM_MODEL_PATH = 'model_ex.tflite'
TM_LABELS_PATH = 'labels_ex.txt'
TM_IMAGE_FILE = "tm_frame.jpg"
CONF_THRESHOLD = 0.70

# --- Moondream Configuration ---
MOONDREAM_WORKER_IMG = "md_worker_frame.jpg"
MOONDREAM_API_URL = "http://localhost:11434/api/generate"
MOONDREAM_MODEL = "moondream:latest"
# This prompt is key! It asks Moondream for a simple, parsable answer.
MOONDREAM_PROMPT = "Is the person in this image happy, sad, or neutral? Answer with only one word: happy, sad, or neutral."

# --- Display Colors (BGR) ---
COLOR_HAPPY = (0, 255, 0)   # Green
COLOR_SAD = (0, 0, 255)     # Red
COLOR_NEUTRAL = (128, 128, 128) # Gray
COLOR_UNCERTAIN = (0, 165, 255) # Orange
TEXT_COLOR = (0, 0, 0)      # Black
FONT = cv.FONT_HERSHEY_SIMPLEX

def ask_moondream(image_path, prompt):
    """
    Asks Moondream about the image and returns the full response text.
    """
    try:
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"[MD Worker Error] Could not read image file: {e}")
        return None
    
    try:
        response = requests.post(
            MOONDREAM_API_URL,
            json={
                "model": MOONDREAM_MODEL,
                "prompt": prompt,
                "images": [image_data],
                "stream": False # We want the full response, not streaming
            },
            timeout=60,
        )
        
        if response.status_code == 200:
            full_response = response.json().get('response', '').strip().lower()
            return full_response
        else:
            print(f"\n[MD Worker Error] Status: {response.status_code}")
            return None
    except Exception as e:
        print(f"\n[MD Worker Error] {e}")
        return None

def moondream_worker(frame_queue, result_queue):
    """
    This function runs in a separate thread.
    It waits for frames, asks Moondream, and posts results.
    """
    print("[MD Worker] Thread started.")
    while True:
        # 1. Get a frame from the main thread
        frame = frame_queue.get()
        if frame is None: # Shutdown signal
            break
            
        # 2. Save the frame to disk
        cv.imwrite(MOONDREAM_WORKER_IMG, frame)
        
        # 3. Ask Moondream
        response = ask_moondream(MOONDREAM_WORKER_IMG, MOONDREAM_PROMPT)
        
        if not response:
            continue # Skip if Moondream failed
            
        # 4. Parse the simple response
        parsed_label = "neutral" # Default
        if "happy" in response:
            parsed_label = "happy"
        elif "sad" in response:
            parsed_label = "sad"
            
        print(f"[MD Worker] Moondream saw: {parsed_label} (Raw: '{response}')")
            
        # 5. Send the result back to the main thread
        try:
            result_queue.put_nowait(parsed_label)
        except queue.Full:
            pass # Main thread is busy, just drop this result

def main():
    # Thread-safe queues for communication
    # maxsize=1 means we only care about the *latest* frame
    frame_queue = queue.Queue(maxsize=1) 
    result_queue = queue.Queue(maxsize=1)
    
    # Start the Moondream worker thread
    md_thread = threading.Thread(
        target=moondream_worker, 
        args=(frame_queue, result_queue), 
        daemon=True # Thread will exit when main script exits
    )
    md_thread.start()

    # --- Setup Models ---
    cap = cv.VideoCapture(0)
    tm_model = TeachableMachineLite(model_path=TM_MODEL_PATH, labels_file_path=TM_LABELS_PATH)
    
    latest_md_label = "neutral" # Stores the last-known MD result
    print("Starting... Press 'ESC' or 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # --- 1. Teachable Machine (Fast) ---
        cv.imwrite(TM_IMAGE_FILE, frame)
        tm_results = tm_model.classify_image(TM_IMAGE_FILE)
        tm_label = tm_results['label']
        tm_confidence = tm_results['confidence']

        # --- 2. Moondream (Slow, from Thread) ---
        
        # Check if the worker thread has a new result for us
        try:
            latest_md_label = result_queue.get_nowait()
        except queue.Empty:
            pass # No new result, just use the old one

        # Push the current frame to the worker thread
        # It won't block. If the worker is busy, it just skips this frame.
        try:
            frame_queue.put_nowait(frame)
        except queue.Full:
            pass

        # --- 3. Combine & Display Logic ---
        
        final_label = "Thinking..."
        final_color = COLOR_NEUTRAL
        
        # Case 1: TM is confident and Moondream agrees
        if tm_confidence > CONF_THRESHOLD and tm_label == latest_md_label:
            final_label = f"Confirmed: {tm_label.capitalize()}"
            final_color = COLOR_HAPPY if tm_label == 'happy' else COLOR_SAD
        
        # Case 2: Models disagree, or TM is not confident
        elif tm_confidence <= CONF_THRESHOLD:
            # Trust Moondream's last-known answer
            final_label = f"MD says: {latest_md_label.capitalize()}"
            if latest_md_label == 'happy': final_color = COLOR_HAPPY
            elif latest_md_label == 'sad': final_color = COLOR_SAD
            else: final_color = COLOR_NEUTRAL
        
        # Case 3: Models disagree and TM is confident (Conflict!)
        elif tm_label != latest_md_label:
            final_label = f"Uncertain (TM: {tm_label}, MD: {latest_md_label})"
            final_color = COLOR_UNCERTAIN
        
        # Case 4: Default to TM if it's confident and MD is neutral
        else: 
            final_label = f"TM: {tm_label.capitalize()}"
            final_color = COLOR_HAPPY if tm_label == 'happy' else COLOR_SAD

        # --- 4. Draw to Screen ---
        
        # Draw the background bar
        cv.rectangle(frame, (0, 0), (frame.shape[1], 40), final_color, -1)
        
        # Draw the final combined text
        cv.putText(frame, final_label, (10, 30), FONT, 0.8, TEXT_COLOR, 2)
        
        # Draw the "raw" model outputs at the bottom
        tm_text = f"TM: {tm_label} ({tm_confidence:.2f})"
        md_text = f"MD: {latest_md_label}"
        cv.putText(frame, tm_text, (10, frame.shape[0] - 30), FONT, 0.6, (255, 255, 255), 2)
        cv.putText(frame, md_text, (10, frame.shape[0] - 10), FONT, 0.6, (255, 255, 255), 2)
        
        cv.imshow('Cam', frame)
        
        # --- 5. Handle Quit ---
        k = cv.waitKey(1)
        if k % 255 == 27 or k % 255 == ord('q'):
            print("Quitting...")
            break

    # Clean up
    cap.release()
    cv.destroyAllWindows()
    frame_queue.put(None) # Send shutdown signal to worker thread
    md_thread.join() # Wait for thread to finish

if __name__ == "__main__":
    main()
