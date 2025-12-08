from nicegui import ui, events
from gpiozero import RGBLED
from gpiozero.pins.mock import MockFactory, MockPWMPin
from gpiozero import Device
from datetime import datetime, timedelta
import zoneinfo
import base64
import colorsys
import json
import os
import uuid
import copy

# --- HARDWARE SETUP ---
is_raspberry_pi = False
try:
    with open('/proc/cpuinfo', 'r') as f:
        if 'Raspberry Pi' in f.read():
            is_raspberry_pi = True
except:
    pass

if not is_raspberry_pi:
    Device.pin_factory = MockFactory(pin_class=MockPWMPin)

light = RGBLED(red=17, green=27, blue=22)

# --- CONFIGURATION ---
NY_TZ = zoneinfo.ZoneInfo("America/New_York")
SAVE_FILE = 'saved_scenes.json'

# --- DATA ---
presets = [
    {'id': 'p1', 'name': 'Sunrise Alarm', 'desc': 'Gradually simulates dawn.', 'icon_color': '#FF9E0B', 
     'intensity_points': [[0,0], [60,80]], 'color_points': [[0, 30], [60, 40]]},
    {'id': 'p2', 'name': 'Deep Focus', 'desc': 'Crisp daylight for work.', 'icon_color': '#00BCD4',
     'intensity_points': [[0,100], [60,100]], 'color_points': [[0, 180], [60, 180]]},
    {'id': 'p3', 'name': 'Wind Down', 'desc': 'Prepare for sleep.', 'icon_color': '#4A148C',
     'intensity_points': [[0,50], [60,0]], 'color_points': [[0, 270], [60, 290]]},
]

default_state = {
    'id': None, 'name': 'New Scene', 'start_time': '22:00', 'end_time': '07:00', 'duration_mins': 540,
    'intensity_points': [[0, 0], [540, 0]], 'color_points': [[0, 0], [540, 0]], 'volume_points': [[0, 0], [540, 0]],
    'sound_track': 'Silence', 'loop_audio': True
}

editing_scene = copy.deepcopy(default_state)
custom_scenes = []
track_options = ['Morning Birds', 'Rainfall', 'White Noise', 'Silence']

# --- FILE PERSISTENCE ---
def load_scenes_from_file():
    global custom_scenes
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r') as f: custom_scenes = json.load(f)
        except: custom_scenes = []

def save_scenes_to_file():
    with open(SAVE_FILE, 'w') as f: json.dump(custom_scenes, f, indent=4)

# Global State
active_graph_key = 'intensity'
active_point_idx = 0
active_graphs = []

# UI Refs
ui_refs = {
    'footer': None, 'slider_time': None, 'slider_val': None, 'color_picker_container': None, 
    'color_picker_element': None, 'point_label': None,
    'tabs': None, 'tab_studio': None, 'tab_my_scenes': None, 'my_scenes_container': None,
    'track_select': None, 'upload_dialog': None, 'scene_name_input': None
}

# --- HELPERS ---
def hex_to_hue(hex_color):
    if not hex_color or not isinstance(hex_color, str): return 0
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6: return 0
    try:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        return h * 360
    except: return 0

def hue_to_hex(hue):
    r, g, b = colorsys.hsv_to_rgb(hue/360, 1, 1)
    return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))

def create_svg_string(points, color_theme, width=1000, height=150, dragging_idx=-1):
    sorted_points = sorted(enumerate(points), key=lambda x: x[1][0])
    
    duration = editing_scene['duration_mins']
    if duration == 0: duration = 1
    
    def to_x(min_val): return (min_val / duration) * width
    y_max = 360 if color_theme == "purple" else 100
    def to_y(val): return height - (val / y_max * height)

    svg = f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<line x1="0" y1="{height/2}" x2="{width}" y2="{height/2}" stroke="#f3f4f6" stroke-width="2" />'

    if sorted_points:
        d = f"M {to_x(sorted_points[0][1][0])},{to_y(sorted_points[0][1][1])}"
        for _, p in sorted_points[1:]:
            d += f" L {to_x(p[0])},{to_y(p[1])}"
        
        line_color = "purple" if color_theme == "purple" else color_theme
        svg += f'<path d="{d}" fill="none" stroke="{line_color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
        
        area_d = d + f" L {to_x(sorted_points[-1][1][0])},{height} L {to_x(sorted_points[0][1][0])},{height} Z"
        svg += f'<path d="{area_d}" fill="{line_color}" fill-opacity="0.1" stroke="none" />'

        for original_idx, p in sorted_points:
            cx = to_x(p[0])
            cy = to_y(p[1])
            is_active = (original_idx == dragging_idx)
            
            r = 14 if is_active else 7
            stroke = "#000" if is_active else line_color
            fill = "#4ADE80" if is_active else ("white" if color_theme != "purple" else hue_to_hex(p[1]))
            
            svg += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{3 if is_active else 2}" />'

    svg += '</svg>'
    return svg

def get_data_uri(svg_string):
    encoded = base64.b64encode(svg_string.encode()).decode()
    return f"data:image/svg+xml;base64,{encoded}"

# --- GRAPH COMPONENT ---
class DraggableGraph:
    def __init__(self, title, key, color):
        self.key = key
        self.title = title
        self.color = color
        self.y_max = 360 if key == 'color' else 100
        self.dragging = False
        self.img = None
        
        with ui.card().classes('w-full p-0 mb-4 border border-gray-200 overflow-hidden select-none group'):
            with ui.row().classes('w-full justify-between p-3 bg-gray-50 border-b border-gray-100'):
                with ui.row().classes('gap-2 items-center'):
                    ui.icon('timeline').classes(f'text-{color}-500')
                    ui.label(title).classes('text-xs font-bold tracking-widest text-gray-700')
                
                with ui.row().classes('gap-1'):
                    ui.button(icon='add', on_click=self.add_point).props('round flat dense size=sm')
                    ui.button(icon='remove', on_click=self.remove_point).props('round flat dense size=sm color=red')

            self.img = ui.interactive_image(
                events=['mousedown', 'mousemove', 'mouseup'], 
                cross=True
            ).classes('w-full h-40 bg-white cursor-crosshair')
            
            self.img.on_mouse(self.handle_mouse)
            self.refresh()

    def refresh(self):
        is_global_active = (active_graph_key == self.key)
        idx = active_point_idx if is_global_active else -1
        points = editing_scene[f'{self.key}_points']
        svg = create_svg_string(points, self.color, dragging_idx=idx)
        self.img.set_source(get_data_uri(svg))
        
        if is_global_active:
            self.img.classes(remove='opacity-50', add='opacity-100')
        else:
            self.img.classes(remove='opacity-100', add='opacity-50')

    def map_from_pixels(self, px_x, px_y):
        duration = editing_scene['duration_mins']
        time_val = (px_x / 1000) * duration
        time_val = max(0, min(time_val, duration))
        val = ((100 - px_y) / 100) * self.y_max
        val = max(0, min(val, self.y_max))
        return [time_val, int(val)]

    def handle_mouse(self, e: events.MouseEventArguments):
        if e.image_x is None: return
        global active_graph_key, active_point_idx
        
        if e.type == 'mousedown':
            show_context_panel()
            
            if active_graph_key != self.key:
                active_graph_key = self.key
                for g in active_graphs: g.refresh()
            
            points = editing_scene[f'{self.key}_points']
            best_dist = 99999
            best_idx = -1
            duration = editing_scene['duration_mins']
            if duration == 0: duration = 1
            
            for i, p in enumerate(points):
                px = (p[0] / duration) * 1000
                py = 100 - (p[1] / self.y_max * 100)
                # Scale py to 150px height
                py_scaled = (py / 100) * 150
                
                dist = ((px - e.image_x)**2 + (py_scaled - e.image_y)**2)**0.5
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i
            
            if best_dist < 200:
                self.dragging = True
                active_point_idx = best_idx
                editing_scene[f'{self.key}_points'][best_idx] = self.map_from_pixels(e.image_x, e.image_y)
                self.refresh()
                update_context_panel()

        elif e.type == 'mousemove' and self.dragging:
            editing_scene[f'{self.key}_points'][active_point_idx] = self.map_from_pixels(e.image_x, e.image_y)
            self.refresh()

        elif e.type == 'mouseup':
            if self.dragging:
                self.dragging = False
                update_context_panel()

    def add_point(self):
        global active_graph_key, active_point_idx
        active_graph_key = self.key
        
        points = editing_scene[f'{self.key}_points']
        mid = editing_scene['duration_mins'] / 2
        offset = len(points) * 20
        new_time = min(mid + offset, editing_scene['duration_mins'])
        
        points.append([new_time, self.y_max/2])
        active_point_idx = len(points) - 1
        
        for g in active_graphs: g.refresh()
        update_context_panel()
        show_context_panel()
        ui.notify(f"Point Added")

    def remove_point(self):
        global active_point_idx
        if active_graph_key != self.key: return

        points = editing_scene[f'{self.key}_points']
        if len(points) > 2:
            points.pop(active_point_idx)
            active_point_idx = max(0, active_point_idx - 1)
            for g in active_graphs: g.refresh()
            update_context_panel()
            ui.notify("Point Removed")
        else:
            ui.notify("Keep at least 2 points", color='red')

# --- LOGIC ---
def update_context_panel():
    points = editing_scene[f'{active_graph_key}_points']
    
    # Sort just for correct labeling
    sorted_indices = sorted(range(len(points)), key=lambda k: points[k][0])
    try: visual_order = sorted_indices.index(active_point_idx) + 1
    except: visual_order = active_point_idx + 1

    if ui_refs['point_label']:
        ui_refs['point_label'].text = f"EDITING {active_graph_key.upper()} POINT #{visual_order}"
    
    if active_point_idx < len(points):
        point = points[active_point_idx]
        if ui_refs['slider_time']:
            ui_refs['slider_time'].props(f'max={editing_scene["duration_mins"]}')
            ui_refs['slider_time'].value = point[0]
            
        if active_graph_key == 'color':
            if ui_refs['color_picker_container']: ui_refs['color_picker_container'].classes(remove='hidden')
            if ui_refs['slider_val']: ui_refs['slider_val'].classes(add='hidden')
            hex_col = hue_to_hex(point[1])
            # FIX: Use props() to set value on element
            if ui_refs['color_picker_element']: 
                ui_refs['color_picker_element'].props(f'model-value="{hex_col}"')
        else:
            if ui_refs['color_picker_container']: ui_refs['color_picker_container'].classes(add='hidden')
            if ui_refs['slider_val']: ui_refs['slider_val'].classes(remove='hidden')
            if ui_refs['slider_val']: ui_refs['slider_val'].value = point[1]

def on_panel_change(source, value):
    points = editing_scene[f'{active_graph_key}_points']
    if source == 'time':
        points[active_point_idx][0] = float(value)
    elif source == 'value':
        points[active_point_idx][1] = int(value)
    elif source == 'color':
        hue = hex_to_hue(value)
        points[active_point_idx][1] = hue

    for g in active_graphs:
        if g.key == active_graph_key: g.refresh()

def calculate_duration():
    FMT = "%H:%M"
    try:
        start = datetime.strptime(editing_scene['start_time'], FMT)
        end = datetime.strptime(editing_scene['end_time'], FMT)
        if end < start: end += timedelta(days=1)
        diff = end - start
        editing_scene['duration_mins'] = int(diff.total_seconds() / 60)
        for g in active_graphs: g.refresh()
    except: pass

def close_context_panel():
    if ui_refs['footer']: ui_refs['footer'].classes(remove='translate-y-0', add='translate-y-full')

def show_context_panel():
    if ui_refs['footer']: ui_refs['footer'].classes(remove='translate-y-full', add='translate-y-0')

def reset_to_default():
    editing_scene.update(copy.deepcopy(default_state))
    editing_scene['id'] = None 
    if ui_refs['scene_name_input']: ui_refs['scene_name_input'].value = 'New Scene'
    calculate_duration()
    ui.notify("Started New Scene")

def load_preset(preset):
    editing_scene.update(copy.deepcopy(default_state))
    editing_scene['id'] = None 
    editing_scene['name'] = f"{preset['name']} (Copy)"
    if 'intensity_points' in preset: editing_scene['intensity_points'] = [p[:] for p in preset['intensity_points']]
    if 'color_points' in preset: editing_scene['color_points'] = [p[:] for p in preset['color_points']]
    if ui_refs['scene_name_input']: ui_refs['scene_name_input'].value = editing_scene['name']
    ui_refs['tabs'].value = ui_refs['tab_studio']
    calculate_duration()
    ui.notify(f"Loaded Template: {preset['name']}")

def load_scene_into_editor(scene_data):
    editing_scene.update(json.loads(json.dumps(scene_data)))
    if ui_refs['scene_name_input']: ui_refs['scene_name_input'].value = editing_scene['name']
    ui_refs['tabs'].value = ui_refs['tab_studio']
    calculate_duration()
    ui.notify(f"Editing: {editing_scene['name']}")

def handle_upload(e: events.UploadEventArguments):
    filename = e.name
    if filename not in track_options:
        track_options.append(filename)
    if ui_refs['track_select']:
        ui_refs['track_select'].options = track_options
        ui_refs['track_select'].value = filename 
        ui_refs['track_select'].update()
    editing_scene['sound_track'] = filename
    ui.notify(f"Imported: {filename}")
    if ui_refs['upload_dialog']: ui_refs['upload_dialog'].close()

def save_scene():
    if not editing_scene['name']:
        ui.notify("Please name your scene", color='red')
        return
    scene_to_save = copy.deepcopy(editing_scene)
    if scene_to_save.get('id'):
        for i, s in enumerate(custom_scenes):
            if s['id'] == scene_to_save['id']:
                custom_scenes[i] = scene_to_save
                break
    else:
        scene_to_save['id'] = str(uuid.uuid4())
        editing_scene['id'] = scene_to_save['id'] 
        custom_scenes.append(scene_to_save)
    save_scenes_to_file()
    refresh_my_scenes_tab()
    ui_refs['tabs'].value = ui_refs['tab_my_scenes']
    ui.notify("Scene Saved", color='positive')

def delete_custom_scene(scene_id):
    global custom_scenes
    custom_scenes = [s for s in custom_scenes if s['id'] != scene_id]
    save_scenes_to_file()
    refresh_my_scenes_tab()
    ui.notify("Scene Deleted", color='red')

def refresh_my_scenes_tab():
    if ui_refs['my_scenes_container']:
        ui_refs['my_scenes_container'].clear()
        with ui_refs['my_scenes_container']:
            if not custom_scenes:
                ui.label("No saved scenes yet.").classes('text-gray-400 italic w-full text-center mt-8')
            for s in custom_scenes:
                with ui.card().classes('w-full p-4 border border-gray-200 shadow-sm flex-row justify-between items-center'):
                    with ui.column().classes('gap-0'):
                        ui.label(s['name']).classes('font-bold text-lg')
                        ui.label(f"{s['start_time']} - {s['end_time']}").classes('text-xs text-gray-500')
                    with ui.row().classes('gap-2'):
                        ui.button(icon='edit', on_click=lambda _, x=s: load_scene_into_editor(x)).props('flat round dense')
                        ui.button(icon='delete', on_click=lambda _, x=s: delete_custom_scene(x['id'])).props('flat round dense color=red')

# --- LAYOUT ---
ui.add_head_html("""<style>body { font-family: 'Inter', sans-serif; background-color: #F3F4F6; }</style>""")
load_scenes_from_file()

with ui.column().classes('w-full max-w-3xl mx-auto p-4 md:p-8 gap-6 pb-64'):
    with ui.row().classes('w-full justify-between items-center'):
        ui.label('SCENE STUDIO').classes('text-2xl font-light tracking-widest text-gray-800')
        ui.icon('wifi').classes('text-green-500')

    with ui.tabs().classes('w-full text-gray-800 bg-white rounded-t-xl') as tabs:
        ui_refs['tabs'] = tabs
        tab_library = ui.tab('Library')
        ui_refs['tab_studio'] = ui.tab('Studio')
        ui_refs['tab_my_scenes'] = ui.tab('My Scenes')

    with ui.tab_panels(tabs, value=tab_library).classes('w-full bg-transparent p-0'):
        with ui.tab_panel(tab_library):
            with ui.grid(columns=3).classes('w-full gap-4'):
                for p in presets:
                    color = p.get('icon_color', 'gray')
                    with ui.card().classes('cursor-pointer hover:shadow-lg transition-all border-l-4').style(f'border-color: {color}').on('click', lambda _, x=p: load_preset(x)):
                        ui.label(p['name']).classes('font-bold')
                        ui.label(p['desc']).classes('text-xs text-gray-500')

        with ui.tab_panel(ui_refs['tab_studio']):
            with ui.card().classes('w-full p-6 rounded-b-xl rounded-tr-xl bg-white shadow-sm mb-6'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label('SCENE SETTINGS').classes('text-xs font-bold text-gray-400')
                    ui.button('New Scene', icon='delete_sweep', on_click=reset_to_default).props('flat dense size=sm color=red')
                with ui.row().classes('w-full items-end gap-6'):
                    ui_refs['scene_name_input'] = ui.input('Name').bind_value(editing_scene, 'name').classes('text-lg font-bold flex-grow')
                    ui.input('Start').bind_value(editing_scene, 'start_time').props('type=time').on('update:model-value', calculate_duration)
                    ui.label('→').classes('pb-4 text-gray-400')
                    ui.input('End').bind_value(editing_scene, 'end_time').props('type=time').on('update:model-value', calculate_duration)
                    with ui.column().classes('items-center bg-gray-100 px-4 py-2 rounded-lg'):
                        ui.label().bind_text_from(editing_scene, 'duration_mins', lambda x: f"{x} min")
                        ui.label('TOTAL').classes('text-[10px] text-gray-500')

            ui.label('CLICK A GRAPH TO EDIT').classes('text-xs font-bold text-gray-400 tracking-widest')
            active_graphs.append(DraggableGraph("VISUAL INTENSITY", "intensity", "orange"))
            active_graphs.append(DraggableGraph("COLOR (HUE)", "color", "purple"))
            active_graphs.append(DraggableGraph("AMPLITUDE", "volume", "blue"))

            with ui.card().classes('w-full p-4 bg-gray-900 text-white shadow-sm mt-6'):
                with ui.row().classes('w-full justify-between items-center'):
                    with ui.column().classes('flex-grow pr-4'):
                        ui.label('AUDIO TRACK').classes('text-[10px] font-bold text-gray-500')
                        ui_refs['track_select'] = ui.select(track_options, value='Morning Birds').bind_value(editing_scene, 'sound_track').props('dark borderless dense').classes('w-full')
                    ui.button('Import', icon='upload', on_click=lambda: ui_refs['upload_dialog'].open()).props('outline dense color=white size=sm')
                    ui.switch('Loop', value=True).props('color=green')
            
            ui.button('SAVE SCENE', on_click=save_scene).classes('w-full mt-4 py-3').props('unelevated color=black')

        with ui.tab_panel(ui_refs['tab_my_scenes']):
            ui_refs['my_scenes_container'] = ui.column().classes('w-full gap-4')
            refresh_my_scenes_tab()

with ui.dialog() as upload_dialog, ui.card():
    ui_refs['upload_dialog'] = upload_dialog
    ui.label('Import Audio File').classes('text-lg font-bold')
    ui.upload(on_upload=handle_upload, auto_upload=True).props('accept=".mp3, .wav"').classes('max-w-full')
    ui.button('Close', on_click=upload_dialog.close).props('flat')

with ui.footer().classes('bg-white border-t border-gray-200 p-6 shadow-[0_-10px_40px_rgba(0,0,0,0.1)] transition-transform duration-300 translate-y-full') as footer:
    ui_refs['footer'] = footer
    with ui.column().classes('w-full max-w-3xl mx-auto'):
        with ui.row().classes('w-full justify-between items-center mb-4'):
            ui_refs['point_label'] = ui.label('EDITING POINT').classes('text-xs font-bold tracking-widest text-gray-400')
            ui.button('Done', icon='check', on_click=close_context_panel).props('flat dense size=sm color=green')
        with ui.row().classes('w-full gap-8 items-start'):
            with ui.column().classes('flex-grow'):
                ui.label('TIME (MINUTES)').classes('text-[10px] font-bold text-gray-400')
                ui_refs['slider_time'] = ui.slider(min=0, max=540, step=1, on_change=lambda e: on_panel_change('time', e.value)).props('label-always color=black')
            with ui.column().classes('flex-grow'):
                ui.label('VALUE SETTING').classes('text-[10px] font-bold text-gray-400')
                ui_refs['slider_val'] = ui.slider(min=0, max=100, step=1, on_change=lambda e: on_panel_change('value', e.value)).props('label-always color=blue')
                with ui.element('div').classes('hidden w-full') as container:
                    ui_refs['color_picker_container'] = container 
                    # Store Element
                    ui_refs['color_picker_element'] = ui.element('q-color').props('no-header no-footer default-view=spectrum format-model=hex class="shadow-0 w-full"').on('update:model-value', lambda e: on_panel_change('color', e.args))
                    ui_refs['color_picker_element'].move(container)

calculate_duration()
update_context_panel()
ui.run(title='Scene Studio', port=8080)
