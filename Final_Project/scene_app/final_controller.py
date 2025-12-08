from nicegui import ui, events, app
import serial
import time
import sys
import threading
import math
import colorsys
import json
import os
import uuid
import copy
import speech_recognition as sr
from datetime import datetime, timedelta

# --- 1. HARDWARE SETUP (ARDUINO) ---
# We use Serial instead of gpiozero because you have an Arduino Ring
# Auto-detect the correct port
possible_ports = ['/dev/ttyACM0', '/dev/ttyUSB0', '/dev/ttyACM1', '/dev/ttyUSB1']
ser = None
BAUD_RATE = 9600

for port in possible_ports:
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=0.1)
        ser.reset_input_buffer()
        print(f"[Hardware] Connected on {port}")
        break 
    except:
        pass

if ser is None:
    print("[WARNING] Arduino not found! Running in simulation mode.")

def send_to_arduino(r, g, b):
    if ser:
        try:
            # Sends R,G,B to the 'Solid Color Driver' on Arduino
            cmd = f"{int(r)},{int(g)},{int(b)}\n"
            ser.write(cmd.encode('utf-8'))
        except:
            pass

# --- 2. DATA & STATE ---
SAVE_FILE = 'saved_scenes.json'

presets = [
    {'id': 'p1', 'name': 'Sunrise Alarm', 'desc': 'Gradually simulates dawn.', 'icon_color': '#FF9E0B', 
     'intensity_points': [[0,0], [30, 50], [60,100]], 'color_points': [[0, 0], [60, 40]]}, # Red to Orange
    {'id': 'p2', 'name': 'Deep Focus', 'desc': 'Crisp daylight for work.', 'icon_color': '#00BCD4',
     'intensity_points': [[0,100], [60,100]], 'color_points': [[0, 180], [60, 180]]}, # Cyan
    {'id': 'p3', 'name': 'Wind Down', 'desc': 'Prepare for sleep.', 'icon_color': '#4A148C',
     'intensity_points': [[0,80], [60,0]], 'color_points': [[0, 270], [60, 290]]}, # Purple
]

default_state = {
    'id': None, 'name': 'New Scene', 'duration_mins': 60,
    'intensity_points': [[0, 0], [60, 100]], 
    'color_points': [[0, 0], [60, 0]], 
    'volume_points': [[0, 0], [60, 0]], # Placeholder for future audio
    'active': False
}

editing_scene = copy.deepcopy(default_state)
custom_scenes = []
active_scene = None
scene_start_time = 0

# --- 3. LOGIC ENGINES ---

# Interpolation: Calculates values between graph points
def get_value_at_time(points, current_minute):
    if not points: return 0
    sorted_points = sorted(points, key=lambda x: x[0])
    
    if current_minute <= sorted_points[0][0]: return sorted_points[0][1]
    if current_minute >= sorted_points[-1][0]: return sorted_points[-1][1]
    
    for i in range(len(sorted_points) - 1):
        p1 = sorted_points[i]
        p2 = sorted_points[i+1]
        if p1[0] <= current_minute <= p2[0]:
            ratio = (current_minute - p1[0]) / (p2[0] - p1[0])
            return p1[1] + ratio * (p2[1] - p1[1])
    return 0

# Hardware Loop: Runs 10 times a second to update lights
def hardware_loop():
    global active_scene, scene_start_time
    
    if active_scene:
        elapsed_mins = (time.time() - scene_start_time) / 60.0
        
        # Stop if duration exceeded (or loop if you prefer)
        if elapsed_mins > active_scene.get('duration_mins', 60):
            elapsed_mins = active_scene.get('duration_mins', 60)

        # 1. Calculate current state from graphs
        intensity = get_value_at_time(active_scene.get('intensity_points', []), elapsed_mins)
        hue = get_value_at_time(active_scene.get('color_points', []), elapsed_mins)
        
        # 2. Convert Logic -> RGB
        brightness = intensity / 100.0
        r, g, b = colorsys.hsv_to_rgb(hue/360.0, 1.0, brightness)
        
        # 3. Send to Arduino
        send_to_arduino(r*255, g*255, b*255)

# Voice Thread: Listens for commands in background
def voice_listener_thread():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    recognizer.pause_threshold = 0.6
    
    print("[Voice] Listening for 'Activate [Scene]', 'Lumos', 'Nox'")
    
    while True:
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = recognizer.listen(source, timeout=None)
                command = recognizer.recognize_google(audio).lower()
                print(f"[Heard]: {command}")
                
                if "lumos" in command:
                    ui.notify("SPELL: LUMOS MAXIMA!")
                    send_to_arduino(255, 255, 255)
                    # Pause scene playback so manual control works
                    global active_scene
                    active_scene = None
                    
                elif "nox" in command or "knocks" in command:
                    ui.notify("SPELL: NOX!")
                    send_to_arduino(0, 0, 0)
                    active_scene = None
                    
                elif "activate" in command or "start" in command:
                    # Try to match scene names
                    for p in presets + custom_scenes:
                        if p['name'].lower() in command:
                            activate_scene(p)
                            break
        except:
            pass

def activate_scene(scene_data):
    global active_scene, scene_start_time
    active_scene = copy.deepcopy(scene_data)
    scene_start_time = time.time()
    ui.notify(f"Playing: {active_scene['name']}")

# --- 4. UI HELPERS ---
def hex_to_hue(hex_color):
    if not hex_color or not isinstance(hex_color, str): return 0
    hex_color = hex_color.lstrip('#')
    try:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        return h * 360
    except: return 0

def hue_to_hex(hue):
    r, g, b = colorsys.hsv_to_rgb(hue/360, 1, 1)
    return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))

def load_scenes_from_file():
    global custom_scenes
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r') as f: custom_scenes = json.load(f)
        except: custom_scenes = []

def save_scenes_to_file():
    with open(SAVE_FILE, 'w') as f: json.dump(custom_scenes, f, indent=4)

# --- 5. UI GRAPH COMPONENT ---
active_graph_key = 'intensity'
active_point_idx = 0
active_graphs = []

# UI Refs for updates
ui_refs = {'slider_time': None, 'slider_val': None, 'color_picker': None, 'point_label': None, 'my_scenes': None}

class DraggableGraph:
    def __init__(self, title, key, color):
        self.key = key
        self.title = title
        self.color = color
        self.y_max = 360 if key == 'color' else 100
        self.img = None
        
        with ui.card().classes('w-full p-0 mb-4 border border-gray-200'):
            with ui.row().classes('w-full justify-between p-3 bg-gray-50'):
                with ui.row().classes('gap-2 items-center'):
                    ui.icon('timeline').classes(f'text-{color}-500')
                    ui.label(title).classes('text-xs font-bold tracking-widest text-gray-700')
                ui.button(icon='add', on_click=self.add_point).props('round flat dense size=sm')

            self.img = ui.interactive_image(cross=True, events=['mousedown', 'mousemove', 'mouseup']).classes('w-full h-40 bg-white cursor-crosshair')
            self.img.on_mouse(self.handle_mouse)
            self.refresh()

    def refresh(self):
        import base64
        points = editing_scene[f'{self.key}_points']
        w, h = 1000, 150
        dur = editing_scene.get('duration_mins', 60)
        if dur == 0: dur = 1
        
        svg = f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'
        svg += f'<rect width="100%" height="100%" fill="white"/>'
        
        # Grid lines
        svg += f'<line x1="0" y1="{h}" x2="{w}" y2="{h}" stroke="#eee" stroke-width="2"/>'
        
        sorted_p = sorted(enumerate(points), key=lambda x: x[1][0])
        
        if sorted_p:
            # Draw Path
            d = f"M {(sorted_p[0][1][0]/dur)*w},{h - (sorted_p[0][1][1]/self.y_max)*h}"
            for _, p in sorted_p[1:]:
                d += f" L {(p[0]/dur)*w},{h - (p[1]/self.y_max)*h}"
            
            line_col = "purple" if self.key == "color" else self.color
            svg += f'<path d="{d}" fill="none" stroke="{line_col}" stroke-width="3"/>'
            
            # Draw Points
            for idx, p in sorted_p:
                cx = (p[0]/dur)*w
                cy = h - (p[1]/self.y_max)*h
                
                is_active = (self.key == active_graph_key and idx == active_point_idx)
                r = 8 if is_active else 5
                stroke = "black" if is_active else line_col
                
                fill_col = hue_to_hex(p[1]) if self.key == 'color' else "white"
                if self.key != 'color': fill_col = self.color
                
                svg += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill_col}" stroke="{stroke}" stroke-width="2" />'

        svg += '</svg>'
        encoded = base64.b64encode(svg.encode()).decode()
        self.img.set_source(f"data:image/svg+xml;base64,{encoded}")

    def add_point(self):
        mid = editing_scene['duration_mins'] / 2
        editing_scene[f'{self.key}_points'].append([mid, self.y_max/2])
        self.refresh()

    def handle_mouse(self, e: events.MouseEventArguments):
        global active_graph_key, active_point_idx
        if e.image_x is None: return
        
        if e.type == 'mousedown':
            active_graph_key = self.key
            points = editing_scene[f'{self.key}_points']
            dur = editing_scene.get('duration_mins', 60)
            
            # Find closest point
            best_dist = 9999
            best_idx = 0
            
            for i, p in enumerate(points):
                px = (p[0]/dur) * 1000
                dist = abs(px - e.image_x)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i
            
            if best_dist < 50: # Only select if close
                active_point_idx = best_idx
                update_editor_panel()
                for g in active_graphs: g.refresh()

# --- 6. PAGE LOGIC ---
def update_editor_panel():
    points = editing_scene[f'{active_graph_key}_points']
    if active_point_idx < len(points):
        pt = points[active_point_idx]
        if ui_refs['slider_time']: 
            ui_refs['slider_time'].value = pt[0]
            ui_refs['slider_time'].props(f'max={editing_scene["duration_mins"]}')
        
        if active_graph_key == 'color':
            if ui_refs['color_picker']: 
                ui_refs['color_picker'].set_visibility(True)
                # NiceGUI color picker needs hex
                # We skip updating value to avoid loop for now or handle carefully
        else:
            if ui_refs['color_picker']: ui_refs['color_picker'].set_visibility(False)
            if ui_refs['slider_val']: 
                ui_refs['slider_val'].set_visibility(True)
                ui_refs['slider_val'].value = pt[1]

def on_param_change(param, value):
    points = editing_scene[f'{active_graph_key}_points']
    if active_point_idx < len(points):
        if param == 'time':
            points[active_point_idx][0] = value
        elif param == 'val':
            points[active_point_idx][1] = value
        elif param == 'color':
            points[active_point_idx][1] = hex_to_hue(value)
            
        for g in active_graphs: 
            if g.key == active_graph_key: g.refresh()

def save_current_scene():
    if not editing_scene['name']:
        ui.notify("Name required", color='red')
        return
        
    scene_copy = copy.deepcopy(editing_scene)
    if not scene_copy.get('id'):
        scene_copy['id'] = str(uuid.uuid4())
        custom_scenes.append(scene_copy)
    else:
        # Update existing
        for i, s in enumerate(custom_scenes):
            if s['id'] == scene_copy['id']:
                custom_scenes[i] = scene_copy
    
    save_scenes_to_file()
    refresh_my_scenes()
    ui.notify("Scene Saved!")

def load_scene_to_edit(s):
    editing_scene.update(copy.deepcopy(s))
    if ui_refs['name_input']: ui_refs['name_input'].value = s['name']
    for g in active_graphs: g.refresh()

def refresh_my_scenes():
    if ui_refs['my_scenes']:
        ui_refs['my_scenes'].clear()
        with ui_refs['my_scenes']:
            for s in custom_scenes:
                with ui.card().classes('w-full flex-row justify-between items-center p-2'):
                    ui.label(s['name']).classes('font-bold')
                    with ui.row():
                        ui.button(icon='play_arrow', on_click=lambda _, x=s: activate_scene(x)).props('flat dense')
                        ui.button(icon='edit', on_click=lambda _, x=s: load_scene_to_edit(x)).props('flat dense')

# --- 7. LAYOUT (GLOBAL MODE) ---
ui.add_head_html("<style>body { background-color: #F3F4F6; }</style>")
load_scenes_from_file()

with ui.column().classes('w-full max-w-3xl mx-auto p-4'):
    ui.label('SCENE STUDIO').classes('text-3xl font-light text-gray-800 mb-6 tracking-widest')

    # PRESETS
    with ui.row().classes('w-full gap-4 mb-8'):
        for p in presets:
            with ui.card().classes('cursor-pointer w-32 h-32 flex flex-col justify-center items-center hover:shadow-lg transition-all').style(f'border-top: 4px solid {p["icon_color"]}').on('click', lambda _, x=p: activate_scene(x)):
                ui.icon('lightbulb', size='md', color=p['icon_color'])
                ui.label(p['name']).classes('text-xs font-bold text-center mt-2')

    with ui.tabs().classes('w-full') as tabs:
        tab_edit = ui.tab('Editor')
        tab_list = ui.tab('My Scenes')

    with ui.tab_panels(tabs, value=tab_edit).classes('w-full bg-transparent'):
        
        # EDITOR TAB
        with ui.tab_panel(tab_edit):
            with ui.card().classes('w-full p-4 bg-white mb-4'):
                with ui.row().classes('w-full items-center gap-4'):
                    ui_refs['name_input'] = ui.input('Scene Name').bind_value(editing_scene, 'name').classes('flex-grow')
                    ui.number('Duration (min)').bind_value(editing_scene, 'duration_mins').classes('w-24')
                    ui.button('TEST', icon='play_arrow', on_click=lambda: activate_scene(editing_scene)).props('unelevated color=black')
                    ui.button('SAVE', icon='save', on_click=save_current_scene).props('outline')

            active_graphs.clear()
            active_graphs.append(DraggableGraph("INTENSITY", "intensity", "orange"))
            active_graphs.append(DraggableGraph("COLOR", "color", "purple"))

            # EDITOR FOOTER
            with ui.card().classes('w-full mt-4 bg-gray-50 border border-gray-200'):
                with ui.row().classes('w-full items-center gap-4'):
                    ui_refs['slider_time'] = ui.slider(min=0, max=60, step=1, on_change=lambda e: on_param_change('time', e.value))
                    ui_refs['slider_val'] = ui.slider(min=0, max=100, step=1, on_change=lambda e: on_param_change('val', e.value))
                    # FIX: Use on_pick instead of on_change for color picker
                    ui_refs['color_picker'] = ui.color_picker(on_pick=lambda e: on_param_change('color', e.color))
                    ui_refs['color_picker'].set_visibility(False)

        # MY SCENES TAB
        with ui.tab_panel(tab_list):
            ui_refs['my_scenes'] = ui.column().classes('w-full gap-2')
            refresh_my_scenes()

# --- STARTUP ---
# 1. Start Voice Thread
t = threading.Thread(target=voice_listener_thread, daemon=True)
t.start()

# 2. Start Hardware Loop
ui.timer(0.1, hardware_loop)

# 3. Start Server
ui.run(title='Light Studio', port=8080, reload=False)