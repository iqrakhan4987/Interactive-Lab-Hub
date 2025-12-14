from flask import Flask, render_template, request, jsonify, send_from_directory
import serial
import time
import json
import threading
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import numpy as np
import sounddevice as sd
import colorsys

# Import Spotify functionality
try:
    from spotify_party import (
        search_spotify_tracks, 
        play_preview_with_analysis, 
        stop_playback,
        microphone_to_leds
    )
    SPOTIFY_AVAILABLE = True
except ImportError:
    SPOTIFY_AVAILABLE = False
    print("Warning: Spotify features not available. Install: pip3 install requests numpy")

app = Flask(__name__)

# --- CONFIGURATION ---
ARDUINO_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600
SCENES_DIR = 'saved_scenes'
MUSIC_DIR = 'music_files'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'ogg'}

# Global state
current_scene = None
scene_thread = None
scene_running = False
music_reactive_running = False
ser = None

# Create directories if they don't exist
for directory in [SCENES_DIR, MUSIC_DIR, UPLOAD_FOLDER]:
    if not os.path.exists(directory):
        os.makedirs(directory)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# --- SETUP: ARDUINO ---
def init_arduino():
    global ser
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.1)
        ser.reset_input_buffer()
        time.sleep(2)
        print(f"Connected to Arduino on {ARDUINO_PORT}")
        return True
    except Exception as e:
        print(f"Error connecting to Arduino: {e}")
        return False

# --- HELPER FUNCTIONS ---
def send_to_arduino(hue, brightness):
    """Send RGB values to Arduino (converts from HSV)"""
    try:
        if ser and ser.is_open:
            # Convert hue (0-255) to RGB
            h = hue / 255.0  # Normalize to 0-1
            s = 1.0          # Full saturation
            v = brightness / 255.0  # Brightness as value
            
            # Convert HSV to RGB
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            
            # Scale to 0-255
            r = int(r * 255)
            g = int(g * 255)
            b = int(b * 255)
            
            # Send in format Arduino expects: "R,G,B\n"
            cmd = f"{r},{g},{b}\n"
            ser.write(cmd.encode('utf-8'))
            
    except Exception as e:
        print(f"Error sending to Arduino: {e}")

def interpolate(start_val, end_val, progress):
    """Linear interpolation between two values"""
    return start_val + (end_val - start_val) * progress

def play_scene(scene_data):
    """Play a scene by interpolating between control points"""
    global scene_running
    
    # Parse scene data
    name = scene_data.get('name', 'Untitled')
    duration_minutes = scene_data.get('duration', 60)
    loop = scene_data.get('loop', False)
    
    hue_points = scene_data.get('hue_points', [{'time': 0, 'value': 0}, {'time': duration_minutes, 'value': 0}])
    brightness_points = scene_data.get('brightness_points', [{'time': 0, 'value': 255}, {'time': duration_minutes, 'value': 255}])
    intensity_points = scene_data.get('intensity_points', [{'time': 0, 'value': 255}, {'time': duration_minutes, 'value': 255}])
    
    print(f"Playing scene: {name}")
    
    while scene_running:
        start_time = time.time()
        duration_seconds = duration_minutes * 60
        
        while scene_running:
            elapsed = time.time() - start_time
            
            if elapsed >= duration_seconds:
                if loop:
                    start_time = time.time()
                    elapsed = 0
                else:
                    scene_running = False
                    break
            
            # Calculate current position in scene (0 to duration_minutes)
            current_time = (elapsed / 60)
            
            # Interpolate hue
            hue = get_value_at_time(hue_points, current_time)
            
            # Interpolate brightness
            brightness = get_value_at_time(brightness_points, current_time)
            
            # Interpolate intensity (affects overall brightness)
            intensity = get_value_at_time(intensity_points, current_time)
            
            # Apply intensity to brightness
            final_brightness = int((brightness / 255) * intensity)
            
            # Send to Arduino
            send_to_arduino(hue, final_brightness)
            
            # Update at ~30 FPS
            time.sleep(0.033)
        
        if not loop:
            break
    
    print("Scene playback stopped")

def get_value_at_time(points, current_time):
    """Get interpolated value at a specific time from control points"""
    # Sort points by time
    sorted_points = sorted(points, key=lambda p: p['time'])
    
    # Find the two points to interpolate between
    if current_time <= sorted_points[0]['time']:
        return sorted_points[0]['value']
    
    if current_time >= sorted_points[-1]['time']:
        return sorted_points[-1]['value']
    
    for i in range(len(sorted_points) - 1):
        p1 = sorted_points[i]
        p2 = sorted_points[i + 1]
        
        if p1['time'] <= current_time <= p2['time']:
            progress = (current_time - p1['time']) / (p2['time'] - p1['time'])
            return interpolate(p1['value'], p2['value'], progress)
    
    return sorted_points[0]['value']

def get_scene_filename(scene_name):
    """Convert scene name to safe filename"""
    safe_name = "".join(c for c in scene_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')
    return f"{safe_name}.json"

# --- API ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scenes', methods=['GET'])
def get_scenes():
    """List all saved scenes"""
    scenes = []
    for filename in os.listdir(SCENES_DIR):
        if filename.endswith('.json'):
            try:
                with open(os.path.join(SCENES_DIR, filename), 'r') as f:
                    scene_data = json.load(f)
                    scenes.append({
                        'name': scene_data.get('name', filename.replace('.json', '')),
                        'filename': filename,
                        'duration': scene_data.get('duration', 0),
                        'loop': scene_data.get('loop', False),
                        'created': scene_data.get('created', 'Unknown')
                    })
            except Exception as e:
                print(f"Error loading scene {filename}: {e}")
    return jsonify(scenes)

@app.route('/api/scene/<filename>', methods=['GET'])
def get_scene(filename):
    """Load a specific scene"""
    try:
        filepath = os.path.join(SCENES_DIR, filename)
        with open(filepath, 'r') as f:
            scene_data = json.load(f)
        return jsonify({'status': 'success', 'scene': scene_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 404

@app.route('/api/scene/save', methods=['POST'])
def save_scene():
    """Save a scene to disk"""
    scene_data = request.json
    scene_name = scene_data.get('name', 'Untitled')
    
    # Add timestamp
    scene_data['created'] = datetime.now().isoformat()
    
    filename = get_scene_filename(scene_name)
    filepath = os.path.join(SCENES_DIR, filename)
    
    try:
        with open(filepath, 'w') as f:
            json.dump(scene_data, f, indent=2)
        return jsonify({
            'status': 'success', 
            'message': f'Scene "{scene_name}" saved successfully',
            'filename': filename
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/scene/delete/<filename>', methods=['DELETE'])
def delete_scene(filename):
    """Delete a saved scene"""
    try:
        filepath = os.path.join(SCENES_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'status': 'success', 'message': 'Scene deleted'})
        else:
            return jsonify({'status': 'error', 'message': 'Scene not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_scene():
    global current_scene, scene_thread, scene_running
    
    scene_data = request.json
    
    # Stop existing scene if running
    if scene_running:
        scene_running = False
        if scene_thread:
            scene_thread.join()
    
    # Start new scene
    current_scene = scene_data
    scene_running = True
    scene_thread = threading.Thread(target=play_scene, args=(scene_data,))
    scene_thread.daemon = True
    scene_thread.start()
    
    return jsonify({'status': 'success', 'message': 'Scene started'})

@app.route('/api/start-by-name/<scene_name>', methods=['POST'])
def start_scene_by_name(scene_name):
    """Start a scene by its name (for voice control)"""
    global current_scene, scene_thread, scene_running
    
    # Find scene file
    filename = get_scene_filename(scene_name)
    filepath = os.path.join(SCENES_DIR, filename)
    
    # Try exact match first
    if not os.path.exists(filepath):
        # Try fuzzy match
        for file in os.listdir(SCENES_DIR):
            if scene_name.lower().replace(' ', '_') in file.lower():
                filename = file
                filepath = os.path.join(SCENES_DIR, file)
                break
    
    if not os.path.exists(filepath):
        return jsonify({'status': 'error', 'message': f'Scene "{scene_name}" not found'}), 404
    
    try:
        with open(filepath, 'r') as f:
            scene_data = json.load(f)
        
        # Stop existing scene if running
        if scene_running:
            scene_running = False
            if scene_thread:
                scene_thread.join()
        
        # Start new scene
        current_scene = scene_data
        scene_running = True
        scene_thread = threading.Thread(target=play_scene, args=(scene_data,))
        scene_thread.daemon = True
        scene_thread.start()
        
        return jsonify({'status': 'success', 'message': f'Playing "{scene_data.get("name")}"'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_scene():
    global scene_running
    scene_running = False
    send_to_arduino(0, 0)  # Turn off LEDs
    return jsonify({'status': 'success', 'message': 'Scene stopped'})

@app.route('/api/test', methods=['POST'])
def test_leds():
    """Test LEDs with a quick rainbow sweep"""
    data = request.json
    hue = data.get('hue', 0)
    brightness = data.get('brightness', 255)
    send_to_arduino(hue, brightness)
    return jsonify({'status': 'success'})

# --- MUSIC REACTIVE MODE ---
def music_reactive_mode(sensitivity=20.0, color_mode='rainbow'):
    """React to live microphone input"""
    global music_reactive_running
    
    print(f"Starting music reactive mode: {color_mode}")
    
    MIN_SPEED = 0.5
    MAX_SPEED = 50.0
    rainbow_offset = 0
    current_speed = MIN_SPEED
    
    def audio_callback(indata, frames, time_info, status):
        nonlocal rainbow_offset, current_speed
        
        if not music_reactive_running:
            return
        
        # Calculate Volume (Root Mean Square)
        volume = np.linalg.norm(indata) * sensitivity
        
        if color_mode == 'rainbow':
            # Rainbow mode - EXACTLY like mic_music.py
            target_speed = MIN_SPEED + volume
            if target_speed > MAX_SPEED:
                target_speed = MAX_SPEED
            
            current_speed = (current_speed * 0.8) + (target_speed * 0.2)
            rainbow_offset = (rainbow_offset + current_speed) % 255
            
            hue = rainbow_offset
            brightness = 255
            
        elif color_mode == 'pulse':
            hue = 170  # Blue
            brightness = min(255, int(volume * 20))
            
        else:  # spectrum
            fft = np.fft.rfft(indata[:, 0])
            freqs = np.abs(fft)
            
            bass = np.mean(freqs[0:10]) if len(freqs) > 10 else 0
            treble = np.mean(freqs[50:100]) if len(freqs) > 100 else 0
            
            hue = 0 if bass > treble else 170
            brightness = min(255, int(volume * 15))
        
        send_to_arduino(hue, brightness)
    
    try:
        with sd.InputStream(callback=audio_callback, blocksize=2048, channels=1):
            while music_reactive_running:
                time.sleep(0.1)
    except Exception as e:
        print(f"Music reactive error: {e}")
        music_reactive_running = False

@app.route('/api/music/start', methods=['POST'])
def start_music_reactive():
    """Start music reactive mode"""
    global music_reactive_running, scene_thread, scene_running
    
    # Stop any running scene
    if scene_running:
        scene_running = False
        if scene_thread:
            scene_thread.join()
    
    data = request.json
    sensitivity = data.get('sensitivity', 20.0)
    color_mode = data.get('color_mode', 'rainbow')
    
    music_reactive_running = True
    scene_thread = threading.Thread(
        target=music_reactive_mode, 
        args=(sensitivity, color_mode)
    )
    scene_thread.daemon = True
    scene_thread.start()
    
    return jsonify({
        'status': 'success', 
        'message': f'Music reactive mode started ({color_mode})'
    })

@app.route('/api/music/stop', methods=['POST'])
def stop_music_reactive():
    """Stop music reactive mode"""
    global music_reactive_running
    music_reactive_running = False
    
    # Also stop Spotify playback if active
    if SPOTIFY_AVAILABLE:
        stop_playback()
    
    send_to_arduino(0, 0)
    return jsonify({'status': 'success', 'message': 'Music reactive mode stopped'})

# --- SPOTIFY INTEGRATION ---
@app.route('/callback')
def spotify_callback():
    """Handle Spotify OAuth callback"""
    return "Authentication successful! You can close this window and return to the app."

@app.route('/api/spotify/search', methods=['POST'])
def spotify_search():
    """Search for tracks on Spotify"""
    if not SPOTIFY_AVAILABLE:
        return jsonify({'status': 'error', 'message': 'Spotify not configured'}), 503
    
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({'status': 'error', 'message': 'No search query'}), 400
    
    try:
        tracks = search_spotify_tracks(query)
        return jsonify({'status': 'success', 'tracks': tracks})
    except Exception as e:
        print(f"Spotify search error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/spotify/play', methods=['POST'])
def spotify_play():
    """Play a Spotify track preview with LED visualization"""
    if not SPOTIFY_AVAILABLE:
        return jsonify({'status': 'error', 'message': 'Spotify not configured'}), 503
    
    global scene_running, music_reactive_running, scene_thread
    
    # Stop any existing playback
    scene_running = False
    music_reactive_running = False
    stop_playback()
    
    data = request.json
    preview_url = data.get('preview_url')
    sensitivity = data.get('sensitivity', 20.0)
    color_mode = data.get('color_mode', 'rainbow')
    
    if not preview_url:
        return jsonify({'status': 'error', 'message': 'No preview URL'}), 400
    
    # Start playback in background thread
    music_reactive_running = True
    scene_thread = threading.Thread(
        target=play_preview_with_analysis,
        args=(preview_url, send_to_arduino, sensitivity, color_mode)
    )
    scene_thread.daemon = True
    scene_thread.start()
    
    return jsonify({'status': 'success', 'message': 'Playing track with LED visualization'})

# --- MP3 FILE UPLOAD & PLAYBACK ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/music/upload', methods=['POST'])
def upload_music():
    """Upload MP3/audio file"""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Invalid file type. Use MP3, WAV, M4A, or OGG'}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        return jsonify({
            'status': 'success',
            'message': f'Uploaded: {filename}',
            'filename': filename
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/music/list', methods=['GET'])
def list_uploaded_music():
    """List all uploaded music files"""
    try:
        files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if allowed_file(filename):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                files.append({
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'uploaded': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                })
        return jsonify({'status': 'success', 'files': files})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/music/play-file', methods=['POST'])
def play_uploaded_file():
    """Play uploaded music file with LED visualization"""
    global scene_running, music_reactive_running, scene_thread
    
    # Stop any existing playback
    scene_running = False
    music_reactive_running = False
    stop_playback()
    
    data = request.json
    filename = data.get('filename')
    sensitivity = data.get('sensitivity', 20.0)
    color_mode = data.get('color_mode', 'rainbow')
    
    if not filename:
        return jsonify({'status': 'error', 'message': 'No filename provided'}), 400
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    
    if not os.path.exists(filepath):
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    
    # Start playback in background thread
    music_reactive_running = True
    scene_thread = threading.Thread(
        target=play_local_file_with_analysis,
        args=(filepath, send_to_arduino, sensitivity, color_mode)
    )
    scene_thread.daemon = True
    scene_thread.start()
    
    return jsonify({'status': 'success', 'message': f'Playing: {filename}'})

@app.route('/api/music/delete-file', methods=['DELETE'])
def delete_uploaded_file():
    """Delete uploaded music file"""
    filename = request.args.get('filename')
    
    if not filename:
        return jsonify({'status': 'error', 'message': 'No filename provided'}), 400
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'status': 'success', 'message': 'File deleted'})
        else:
            return jsonify({'status': 'error', 'message': 'File not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def play_local_file_with_analysis(filepath, send_to_arduino_func, sensitivity, color_mode):
    """Play local audio file with microphone-based LED visualization"""
    import subprocess
    
    try:
        print(f"Playing local file: {filepath}")
        
        # Convert to WAV if needed
        if filepath.endswith('.wav'):
            wav_file = filepath
        else:
            wav_file = '/tmp/converted_audio.wav'
            result = subprocess.run([
                'ffmpeg', '-y', '-i', filepath,
                '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '1',
                wav_file
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                return
        
        print("Starting playback + microphone listening...")
        
        # Import from spotify_party
        from spotify_party import play_audio_file
        import spotify_party
        
        # Set global flag
        spotify_party.audio_monitor_active = True
        
        # Start playback
        play_thread = threading.Thread(target=play_audio_file, args=(wav_file,))
        play_thread.daemon = True
        play_thread.start()
        
        # Start microphone listening
        mic_thread = threading.Thread(
            target=microphone_to_leds,
            args=(send_to_arduino_func, sensitivity, color_mode)
        )
        mic_thread.daemon = True
        mic_thread.start()
        
        # Wait for playback
        play_thread.join()
        
        # Stop microphone
        spotify_party.audio_monitor_active = False
        mic_thread.join(timeout=2)
        
        print("Playback complete")
        
    except Exception as e:
        print(f"Playback error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if init_arduino():
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("Failed to initialize Arduino. Please check connection.")