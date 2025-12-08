from nicegui import ui
import serial
import time
import sys
import json
import os

# --- 1. HARDWARE SETUP ---
possible_ports = ['/dev/ttyACM0', '/dev/ttyUSB0', '/dev/ttyACM1', '/dev/ttyUSB1']
ser = None

for port in possible_ports:
    try:
        ser = serial.Serial(port, 9600, timeout=0.1)
        ser.reset_input_buffer()
        print(f"[Hardware] Connected on {port}")
        break 
    except:
        pass

if ser is None:
    print("[WARNING] Arduino not found! Simulation mode.")

def send_to_led(r, g, b):
    """Sends RGB values to Arduino"""
    if ser:
        try:
            cmd = f"{int(r)},{int(g)},{int(b)}\n"
            ser.write(cmd.encode('utf-8'))
        except:
            pass

# --- 2. DATA MANAGEMENT ---
SAVE_FILE = 'my_colors.json'
saved_colors = []

if os.path.exists(SAVE_FILE):
    try:
        with open(SAVE_FILE, 'r') as f:
            saved_colors = json.load(f)
    except:
        saved_colors = []

def save_data():
    with open(SAVE_FILE, 'w') as f:
        json.dump(saved_colors, f, indent=4)

# --- 3. LOGIC ---
creator_state = {
    'name': 'My New Color',
    'hex': '#FF0000',
    'brightness': 100
}

# UI Reference for the preview box
preview_box = None

def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def apply_color(hex_col, brightness_percent):
    r, g, b = hex_to_rgb(hex_col)
    factor = brightness_percent / 100.0
    send_to_led(r * factor, g * factor, b * factor)

def update_preview_ui():
    """Updates the color box directly (No timer needed)"""
    if preview_box:
        hex_c = creator_state['hex']
        opacity = creator_state['brightness'] / 100.0
        preview_box.style(f'background-color: {hex_c}; opacity: {opacity}')

def save_current_creation():
    if not creator_state['name']:
        ui.notify("Please enter a name!", color='red')
        return

    new_entry = {
        'id': time.time(),
        'name': creator_state['name'],
        'hex': creator_state['hex'],
        'brightness': creator_state['brightness']
    }
    saved_colors.append(new_entry)
    save_data()
    refresh_library()
    ui.notify(f"Saved '{new_entry['name']}'")

def delete_color(item):
    saved_colors.remove(item)
    save_data()
    refresh_library()

# --- 4. USER INTERFACE ---
@ui.page('/')
async def main_page():
    global preview_box
    
    # Header
    with ui.header().classes('bg-blue-900 text-white p-4'):
        ui.label('LED COLOR STATION').classes('text-xl font-bold tracking-widest')

    with ui.column().classes('w-full max-w-2xl mx-auto p-6 gap-8'):
        
        # --- CREATOR PANEL ---
        with ui.card().classes('w-full p-6 bg-gray-50 border-2 border-blue-100'):
            ui.label('CREATE A COLOR').classes('text-sm font-bold text-gray-400 mb-4')
            
            ui.input('Color Name').bind_value(creator_state, 'name').classes('w-full text-lg font-bold mb-4')
            
            with ui.row().classes('w-full items-start gap-8'):
                # Color Picker
                with ui.column().classes('items-center'):
                    ui.label('Pick Color')
                    ui.color_picker(on_pick=lambda e: [creator_state.update({'hex': e.color}), update_preview_ui()]) \
                        .bind_value(creator_state, 'hex')
                
                # Brightness Slider
                with ui.column().classes('flex-grow'):
                    ui.label('Set Brightness')
                    ui.slider(min=0, max=100, step=1, on_change=update_preview_ui).bind_value(creator_state, 'brightness').classes('w-full')
                    
                    # Preview Box
                    with ui.row().classes('items-center mt-4'):
                        ui.label('Preview: ')
                        preview_box = ui.element('div').classes('w-16 h-16 rounded-full border shadow-sm transition-all')
                        update_preview_ui() # Set initial color

            # Buttons
            with ui.row().classes('w-full justify-end gap-4 mt-6'):
                ui.button('TEST ON LED', icon='lightbulb', \
                    on_click=lambda: apply_color(creator_state['hex'], creator_state['brightness'])) \
                    .props('outline')
                
                ui.button('SAVE PRESET', icon='save', on_click=save_current_scene_wrapper) \
                    .props('unelevated color=blue-900')

        # --- LIBRARY PANEL ---
        ui.label('SAVED COLORS').classes('text-sm font-bold text-gray-400 mt-4')
        
        library_container = ui.column().classes('w-full gap-3')

        def refresh_library_ui():
            library_container.clear()
            with library_container:
                if not saved_colors:
                    ui.label('No colors saved yet. Create one above!').classes('italic text-gray-400')
                
                for item in saved_colors:
                    with ui.card().classes('w-full flex-row justify-between items-center p-3 border-l-8').style(f'border-left-color: {item["hex"]}'):
                        
                        with ui.column().classes('gap-0'):
                            ui.label(item['name']).classes('font-bold text-lg')
                            ui.label(f"Brightness: {item['brightness']}%").classes('text-xs text-gray-500')
                        
                        with ui.row().classes('items-center gap-2'):
                            ui.button(icon='play_arrow', \
                                on_click=lambda _, x=item: apply_color(x['hex'], x['brightness'])) \
                                .props('round color=green icon-size=md')
                            
                            ui.button(icon='stop', \
                                on_click=lambda: send_to_led(0,0,0)) \
                                .props('outline round color=red size=sm')
                            
                            ui.button(icon='delete', \
                                on_click=lambda _, x=item: delete_color(x)) \
                                .props('flat round size=sm text-color=grey')

        global refresh_library
        refresh_library = refresh_library_ui
        refresh_library()

# Wrapper to handle async event loop safely for the save button
def save_current_scene_wrapper():
    save_current_creation()

ui.run(title='LED Color Station', port=8080)