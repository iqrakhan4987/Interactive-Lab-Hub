from teachable_machine_lite import TeachableMachineLite
import cv2 as cv
import numpy as np
import random

# --- Configuration ---
MODEL_PATH = 'model_ex.tflite'
LABELS_PATH = 'labels_ex.txt'
CONF_THRESHOLD = 0.70  # Only show color if confidence is above 70%
IMAGE_FILE_NAME = "frame.jpg"

# --- Colors (in BGR format) ---
COLOR_SAD = (0, 0, 0)         # Black (BGR)
COLOR_NEUTRAL = (128, 128, 128) # Gray
TEXT_COLOR = (0, 0, 0)      # Black
FONT = cv.FONT_HERSHEY_SIMPLEX

# Rainbow colors for happy mood (in BGR format)
RAINBOW_COLORS = [
    (0, 0, 255),      # Red
    (0, 127, 255),    # Orange
    (0, 255, 255),    # Yellow
    (0, 255, 0),      # Green
    (255, 0, 0),      # Blue
    (130, 0, 75),     # Indigo
    (211, 0, 148)     # Violet
]

# --- Drawing Settings ---
BRUSH_SIZE = 20
CANVAS_WIDTH = 640
CANVAS_HEIGHT = 480

# --- Setup ---
cap = cv.VideoCapture(0)
tm_model = TeachableMachineLite(model_path=MODEL_PATH, labels_file_path=LABELS_PATH)

# Create a blank white canvas for drawing
canvas = np.ones((CANVAS_HEIGHT, CANVAS_WIDTH, 3), dtype=np.uint8) * 255

# Variables for automatic drawing
drawing_x = CANVAS_WIDTH // 2
drawing_y = CANVAS_HEIGHT // 2
current_color = COLOR_NEUTRAL
rainbow_index = 0

# Create windows
cv.namedWindow('Mood Board')
cv.namedWindow('Cam')

print("Instructions:")
print("- The mood board will draw automatically based on your mood")
print("- Happy = Rainbow colors, Sad = Black")
print("- Press 'c' to clear the canvas")
print("- Press 'ESC' to exit")

frame_count = 0

while True:
    
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture frame.")
        break

    # 1. Save frame for classification
    cv.imwrite(IMAGE_FILE_NAME, frame)
    
    # 2. Classify the image
    results = tm_model.classify_image(IMAGE_FILE_NAME)
    
    # 3. Get the label and confidence
    label = results['label']
    confidence = results['confidence']
    
    # --- Update Drawing Color Based on Mood ---
    # Convert label to lowercase and check if it contains the mood words
    label_lower = label.lower()
    
    if confidence > CONF_THRESHOLD:
        if 'happy' in label_lower:
            # Cycle through rainbow colors for happy
            current_color = RAINBOW_COLORS[rainbow_index % len(RAINBOW_COLORS)]
            display_color = current_color
            rainbow_index = (rainbow_index + 1) % len(RAINBOW_COLORS)
        elif 'sad' in label_lower:
            display_color = COLOR_SAD
            current_color = COLOR_SAD
        else:
            display_color = COLOR_NEUTRAL
            current_color = COLOR_NEUTRAL
    else:
        display_color = COLOR_NEUTRAL
        current_color = COLOR_NEUTRAL
    
    # --- Automatic Drawing Logic ---
    # Draw only every few frames to make it smoother
    if frame_count % 2 == 0:  # Draw every 2 frames
        # Store previous position
        prev_x, prev_y = drawing_x, drawing_y
        
        # Random walk pattern - moves in random directions
        dx = random.randint(-20, 20)
        dy = random.randint(-20, 20)
        
        # Update position with bounds checking
        drawing_x = max(50, min(CANVAS_WIDTH - 50, drawing_x + dx))
        drawing_y = max(50, min(CANVAS_HEIGHT - 50, drawing_y + dy))
        
        # Draw line from previous position to new position
        cv.line(canvas, (prev_x, prev_y), (drawing_x, drawing_y), current_color, BRUSH_SIZE)
    
    frame_count += 1
    
    # Create the text to display
    display_text = f"{label}: {confidence:.2f}"
    
    # Draw a filled rectangle at the top for the text background
    cv.rectangle(frame, (0, 0), (frame.shape[1], 40), display_color, -1) 
    
    # Draw the text on top of the rectangle
    cv.putText(frame, display_text, (10, 30), FONT, 1, TEXT_COLOR, 2)
    
    # Add color indicator to canvas (draw on a copy to avoid permanent overlay)
    canvas_display = canvas.copy()
    cv.rectangle(canvas_display, (10, 10), (60, 60), current_color, -1)
    cv.rectangle(canvas_display, (10, 10), (60, 60), (0, 0, 0), 2)
    
    # Add mood text on canvas
    cv.putText(canvas_display, f"{label}", (70, 40), FONT, 0.8, TEXT_COLOR, 2)
    
    # Display both windows
    cv.imshow('Cam', frame)
    cv.imshow('Mood Board', canvas_display)
    
    k = cv.waitKey(1)
    
    # Clear canvas with 'c' key
    if k & 0xFF == ord('c'):
        canvas = np.ones((CANVAS_HEIGHT, CANVAS_WIDTH, 3), dtype=np.uint8) * 255
        drawing_x = CANVAS_WIDTH // 2
        drawing_y = CANVAS_HEIGHT // 2
        print("Canvas cleared!")
    
    # Exit with ESC key
    if k & 0xFF == 27:
        break

# Clean up
cap.release()
cv.destroyAllWindows()
