"""
Spotify Integration - Uses Microphone for LED Reactions (like mic_music.py)
"""

import os
import threading
import time
import numpy as np
import subprocess
import requests
import sounddevice as sd

# Spotify Configuration
SPOTIFY_CLIENT_ID = '6f88ee6cac804f87abbc237a45898276'
SPOTIFY_CLIENT_SECRET = 'a86ce1c94308486aa80c34d9f41153ae'

# Audio monitoring
audio_monitor_active = False

def get_spotify_token():
    """Get access token using Client Credentials"""
    auth_url = 'https://accounts.spotify.com/api/token'
    
    auth_response = requests.post(auth_url, {
        'grant_type': 'client_credentials',
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET,
    })
    
    if auth_response.status_code == 200:
        return auth_response.json()['access_token']
    else:
        print(f"Auth error: {auth_response.status_code}")
        return None

def search_spotify_tracks(query, limit=20):
    """Search for tracks on Spotify - ONLY RETURN TRACKS WITH PREVIEWS!"""
    try:
        token = get_spotify_token()
        if not token:
            print("Failed to get Spotify token")
            return []
        
        search_url = 'https://api.spotify.com/v1/search'
        headers = {'Authorization': f'Bearer {token}'}
        params = {
            'q': query,
            'type': 'track',
            'limit': 50
        }
        
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Search error: {response.status_code}")
            return []
        
        results = response.json()
        tracks = []
        
        for item in results['tracks']['items']:
            if item['preview_url']:
                tracks.append({
                    'id': item['id'],
                    'name': item['name'],
                    'artist': ', '.join([artist['name'] for artist in item['artists']]),
                    'album': item['album']['name'],
                    'preview_url': item['preview_url'],
                    'duration_ms': item['duration_ms'],
                    'image': item['album']['images'][0]['url'] if item['album']['images'] else None
                })
            
            if len(tracks) >= limit:
                break
        
        print(f"Found {len(tracks)} tracks WITH PREVIEWS")
        return tracks
        
    except Exception as e:
        print(f"Search error: {e}")
        return []

def play_preview_with_analysis(preview_url, send_to_arduino_func, sensitivity=20.0, color_mode='rainbow'):
    """
    Download and play preview while listening to microphone for LED reactions
    EXACTLY like mic_music.py
    """
    global audio_monitor_active
    
    try:
        print(f"Downloading preview...")
        
        # Download preview MP3
        response = requests.get(preview_url)
        if response.status_code != 200:
            print(f"Failed to download preview")
            return
            
        preview_file = '/tmp/spotify_preview.mp3'
        with open(preview_file, 'wb') as f:
            f.write(response.content)
        
        print("Converting to WAV...")
        wav_file = '/tmp/spotify_preview.wav'
        result = subprocess.run([
            'ffmpeg', '-y', '-i', preview_file, 
            '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '1',
            wav_file
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return
        
        print("Starting playback + microphone listening...")
        audio_monitor_active = True
        
        # Start playback
        play_thread = threading.Thread(target=play_audio_file, args=(wav_file,))
        play_thread.daemon = True
        play_thread.start()
        
        # Start microphone listening (like mic_music.py)
        mic_thread = threading.Thread(
            target=microphone_to_leds,
            args=(send_to_arduino_func, sensitivity, color_mode)
        )
        mic_thread.daemon = True
        mic_thread.start()
        
        # Wait for playback to finish
        play_thread.join(timeout=35)
        
        # Stop microphone
        audio_monitor_active = False
        mic_thread.join(timeout=2)
        
        print("Playback complete")
        
    except Exception as e:
        print(f"Playback error: {e}")
        audio_monitor_active = False

def microphone_to_leds(send_to_arduino_func, sensitivity, color_mode):
    """
    Listen to microphone and control LEDs - EXACTLY like mic_music.py
    """
    global audio_monitor_active
    
    MIN_SPEED = 0.5
    MAX_SPEED = 50.0
    
    rainbow_offset = 0
    current_speed = MIN_SPEED
    
    def audio_callback(indata, frames, time_info, status):
        nonlocal rainbow_offset, current_speed
        
        if not audio_monitor_active:
            return
        
        # Calculate Volume (RMS) - EXACTLY like mic_music.py
        volume = np.linalg.norm(indata) * sensitivity
        
        if color_mode == 'rainbow':
            # Rainbow mode - EXACTLY like mic_music.py
            target_speed = MIN_SPEED + volume
            
            if target_speed > MAX_SPEED:
                target_speed = MAX_SPEED
            
            # Smooth speed change
            current_speed = (current_speed * 0.8) + (target_speed * 0.2)
            
            # Advance rainbow
            rainbow_offset = (rainbow_offset + current_speed) % 255
            
            hue = rainbow_offset
            brightness = 255
            
        elif color_mode == 'pulse':
            # Pulse mode
            hue = 170  # Blue
            brightness = min(255, int(volume * 20))
            
        else:  # spectrum
            # Spectrum mode
            fft = np.fft.rfft(indata[:, 0])
            freqs = np.abs(fft)
            
            bass = np.mean(freqs[0:10]) if len(freqs) > 10 else 0
            treble = np.mean(freqs[50:100]) if len(freqs) > 100 else 0
            
            hue = 0 if bass > treble else 170
            brightness = min(255, int(volume * 15))
        
        # Send to Arduino
        send_to_arduino_func(hue, brightness)
    
    try:
        # Open microphone stream - EXACTLY like mic_music.py
        with sd.InputStream(callback=audio_callback, blocksize=2048, channels=1):
            while audio_monitor_active:
                time.sleep(0.1)
                
    except Exception as e:
        print(f"Microphone error: {e}")

def play_audio_file(wav_file):
    """Play audio through Bluetooth speaker"""
    try:
        subprocess.run(['paplay', wav_file], capture_output=True)
    except Exception as e:
        print(f"Audio playback error: {e}")

def stop_playback():
    """Stop current playback"""
    global audio_monitor_active
    audio_monitor_active = False
    
    try:
        subprocess.run(['pkill', 'paplay'], capture_output=True)
        subprocess.run(['pkill', 'aplay'], capture_output=True)
    except:
        pass

# Export functions
__all__ = [
    'search_spotify_tracks',
    'play_preview_with_analysis',
    'stop_playback',
    'microphone_to_leds'
]