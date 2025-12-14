#!/usr/bin/env python3
"""
Simple Spotify Authentication - No Web Server Needed
"""
import sys

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    print("Error: spotipy not installed")
    print("Run: pip3 install spotipy")
    sys.exit(1)

# YOUR CREDENTIALS HERE
SPOTIFY_CLIENT_ID = '6f88ee6cac804f87abbc237a45898276'
SPOTIFY_CLIENT_SECRET = 'a86ce1c94308486aa80c34d9f41153ae'

print("="*70)
print("SPOTIFY AUTHENTICATION - SIMPLE METHOD")
print("="*70)

# Create auth manager
auth_manager = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri='http://127.0.0.1:5000/callback',
    scope='user-read-playback-state user-modify-playback-state',
    cache_path='.spotify_cache',
    open_browser=False
)

# Get the authorization URL
auth_url = auth_manager.get_authorize_url()

print("\nINSTRUCTIONS:")
print("\n1. Copy this URL and open it in your browser:")
print("-" * 70)
print(auth_url)
print("-" * 70)

print("\n2. Click 'Agree' on the Spotify page")

print("\n3. After clicking Agree, you'll see a page that says:")
print("   'This site can't be reached' or keeps loading")
print("   --> THIS IS EXPECTED! Don't worry!")

print("\n4. Look at your browser's ADDRESS BAR")
print("   Copy the ENTIRE URL from there")
print("   It will look like:")
print("   http://192.168.1.158:5000/callback?code=AQA...")

print("\n5. Paste that URL below and press Enter")
print("="*70)

# Wait for user to paste the redirect URL
response_url = input("\nPaste the full redirect URL here: ").strip()

# Extract the code and get token
try:
    code = auth_manager.parse_response_code(response_url)
    print("\nGetting access token...")
    token_info = auth_manager.get_access_token(code, as_dict=True)
    
    print("\n" + "="*70)
    print("SUCCESS! Spotify authentication complete!")
    print("="*70)
    print(f"\nToken saved to: .spotify_cache")
    print(f"Token expires in: {token_info['expires_in']} seconds (~1 hour)")
    print("\nYou can now run your Flask app:")
    print("   python3 scene.py")
    print("\nSpotify search will now work in the web interface!")
    
except Exception as e:
    print(f"\nError: {e}")
    print("\nTroubleshooting:")
    print("   - Make sure you pasted the COMPLETE URL including ?code=...")
    print("   - Check that your redirect URI in Spotify settings is:")
    print("     http://192.168.1.158:5000/callback")
    print("   - Verify your Client Secret is correct")
