from teachable_machine_lite import TeachableMachineLite
import cv2 as cv

# --- Configuration ---
MODEL_PATH = 'model_ex.tflite'
LABELS_PATH = 'labels_ex.txt'
CONF_THRESHOLD = 0.70  # Only show color if confidence is above 70%
IMAGE_FILE_NAME = "frame.jpg"

# --- Colors (in BGR format) ---
COLOR_HAPPY = (0, 255, 0)   # Green
COLOR_SAD = (0, 0, 255)     # Red
COLOR_NEUTRAL = (128, 128, 128) # Gray
TEXT_COLOR = (0, 0, 0)      # Black
FONT = cv.FONT_HERSHEY_SIMPLEX

# --- Setup ---
cap = cv.VideoCapture(0)
tm_model = TeachableMachineLite(model_path=MODEL_PATH, labels_file_path=LABELS_PATH)

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
    
    # --- Visualization Logic ---
    
    # Start with a neutral color
    display_color = COLOR_NEUTRAL

    # Check confidence threshold
    if confidence > CONF_THRESHOLD:
        if label == 'happy':
            display_color = COLOR_HAPPY
        elif label == 'sad':
            display_color = COLOR_SAD
    
    # Create the text to display
    display_text = f"{label}: {confidence:.2f}"
    
    # Draw a filled rectangle at the top for the text background
    # Arguments: (image, start_point, end_point, color, thickness)
    cv.rectangle(frame, (0, 0), (frame.shape[1], 40), display_color, -1) 
    
    # Draw the text on top of the rectangle
    # Arguments: (image, text, origin, font, scale, color, thickness)
    cv.putText(frame, display_text, (10, 30), FONT, 1, TEXT_COLOR, 2)
    
    # --- End Visualization Logic ---

    # Display the final, modified frame
    cv.imshow('Cam', frame)
    
    k = cv.waitKey(1)
    if k% 255 == 27:
        # press ESC to close camera view.
        break

# Clean up
cap.release()
cv.destroyAllWindows()
