from nicegui import ui
from gpiozero import RGBLED
from gpiozero.pins.mock import MockFactory, MockPWMPin
from gpiozero import Device

# --- HARDWARE MOCK ---
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

# --- DATA ---
default_scenes = [
    {'id': 'sunrise', 'name': 'Sunrise', 'color': '#FFAA00', 'sound': 'Morning Birds', 'duration': 30, 'intensity': 0.8, 'icon': 'wb_sunny'},
    {'id': 'night', 'name': 'Night Wind', 'color': '#1a237e', 'sound': 'White Noise', 'duration': 15, 'intensity': 0.2, 'icon': 'nights_stay'},
    {'id': 'focus', 'name': 'Deep Focus', 'color': '#e0f7fa', 'sound': 'Rainfall', 'duration': 0, 'intensity': 1.0, 'icon': 'menu_book'},
    {'id': 'disco', 'name': 'Party Mode', 'color': '#ff00ff', 'sound': 'Lofi Beats', 'duration': 0, 'intensity': 1.0, 'icon': 'music_note'},
]

custom_scenes = [] 

editing_scene = {
    'name': '', 'color': '#ffffff', 'sound': 'Silence', 
    'duration': 15, 'intensity': 0.8, 'start_time': '07:00'
}

# --- LOGIC ---

def update_chart():
    """Updates the visual graph."""
    duration = editing_scene['duration']
    peak = editing_scene['intensity'] * 100
    color = editing_scene['color']
    
    curve_chart.options['xAxis']['data'] = ['Start', f'{duration//2}m', f'{duration}m']
    curve_chart.options['series'][0]['data'] = [0, peak/2, peak]
    curve_chart.options['series'][0]['lineStyle']['color'] = color
    curve_chart.options['series'][0]['areaStyle']['color'] = color
    
    curve_chart.update()

def on_color_change(color_val):
    editing_scene['color'] = color_val
    header_row.style(f'background-color: {color_val}')
    update_chart()

def open_editor(scene_data=None, is_new=False):
    global editing_scene
    
    if scene_data:
        editing_scene.update(scene_data)
    else:
        editing_scene.update({'name': 'New Scene', 'color': '#FF0000', 'duration': 20, 'intensity': 0.5})
    
    name_input.value = editing_scene['name']
    
    # Update Quasar Color Element manually
    picker.props(f'model-value="{editing_scene["color"]}"')
    
    duration_slider.value = editing_scene['duration']
    intensity_slider.value = editing_scene['intensity']
    
    header_row.style(f'background-color: {editing_scene["color"]}')
    
    is_preset = not is_new and any(s['id'] == scene_data.get('id') for s in default_scenes)
    name_input.props('readonly' if is_preset else '')
    
    update_chart()
    dialog.open()

def save_custom_scene():
    new_scene = editing_scene.copy()
    new_scene['icon'] = 'fingerprint'
    custom_scenes.append(new_scene)
    refresh_custom_list()
    dialog.close()
    ui.notify(f"Created Scene: {new_scene['name']}")

def delete_custom_scene(scene):
    custom_scenes.remove(scene)
    refresh_custom_list()

def activate_scene():
    ui.notify(f"Activated {editing_scene['name']}.")
    dialog.close()

# --- UI LAYOUT ---
ui.colors(primary='#B58900', secondary='#586E75', accent='#cb4b16')
bg_color = '#FDF6E3' 

with ui.column().classes('w-full min-h-screen p-4').style(f'background-color: {bg_color}'):
    
    ui.label('SCENE').classes('text-4xl font-light tracking-[0.3em] text-gray-600 mb-6 mx-auto mt-4')

    # --- TABS ---
    with ui.tabs().classes('w-full text-gray-600') as tabs:
        preset_tab = ui.tab('PRESETS')
        custom_tab = ui.tab('MY SCENES') 

    with ui.tab_panels(tabs, value=preset_tab).classes('w-full bg-transparent'):
        
        # PRESETS
        with ui.tab_panel(preset_tab):
            with ui.grid(columns=2).classes('w-full gap-4'):
                for scene in default_scenes:
                    with ui.card().classes('cursor-pointer hover:shadow-md transition-all').on('click', lambda s=scene: open_editor(s)):
                        with ui.row().classes('items-center no-wrap'):
                            ui.icon(scene['icon'], color=scene['color']).classes('text-3xl')
                            with ui.column().classes('gap-0'):
                                ui.label(scene['name']).classes('font-bold text-sm')
                                ui.label(f"{scene['sound']}").classes('text-xs opacity-60')

        # MY SCENES
        with ui.tab_panel(custom_tab):
            container = ui.column().classes('w-full gap-4')
            def refresh_custom_list():
                container.clear()
                with container:
                    if not custom_scenes:
                        ui.label('No custom scenes yet.').classes('text-center w-full opacity-40 mt-4')
                    for scene in custom_scenes:
                        with ui.card().classes('w-full flex-row justify-between items-center'):
                            with ui.row().classes('items-center cursor-pointer').on('click', lambda s=scene: open_editor(s)):
                                ui.icon('fingerprint', color=scene['color'])
                                ui.label(scene['name'])
                            ui.button(icon='delete', on_click=lambda s=scene: delete_custom_scene(s)).props('flat dense color=red')
            refresh_custom_list()
            ui.button(icon='add', on_click=lambda: open_editor(None, is_new=True)).classes('fixed bottom-8 right-8 rounded-full shadow-lg w-14 h-14')

    # --- THE EDITOR DIALOG ---
    # FIX IS HERE: We set height to 80vh (80% viewport height) and flex column
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-md p-0 h-[80vh] flex flex-col'):
        
        # Header (Fixed at top, does not scroll)
        header_row = ui.row().classes('w-full h-16 items-center justify-center transition-colors duration-300 shrink-0')
        
        # Scrollable Area (The middle part)
        with ui.scroll_area().classes('p-6 w-full flex-grow'):
            
            # Name
            with ui.row().classes('w-full justify-between items-center mb-4'):
                name_input = ui.input('Scene Name').bind_value(editing_scene, 'name').classes('text-lg font-bold w-full')

            # Graph
            curve_chart = ui.echart({
                'grid': {'top': 10, 'bottom': 20, 'left': 30, 'right': 10},
                'xAxis': {'type': 'category', 'data': []},
                'yAxis': {'type': 'value', 'max': 100},
                'series': [{
                    'data': [], 'type': 'line', 'smooth': True,
                    'areaStyle': {'color': '#000'}, 'lineStyle': {'color': '#000'}
                }]
            }).classes('h-24 w-full mb-6')
            
            # Controls
            with ui.row().classes('w-full justify-between mb-2'):
                duration_slider = ui.slider(min=0, max=60, step=5, on_change=update_chart).bind_value(editing_scene, 'duration').props('label="Duration"')
                ui.label('Duration').classes('text-xs text-gray-400')
            
            with ui.row().classes('w-full justify-between mb-6'):
                intensity_slider = ui.slider(min=0.1, max=1.0, step=0.1, on_change=update_chart).bind_value(editing_scene, 'intensity').props('label="Intensity"')
                ui.label('Intensity').classes('text-xs text-gray-400')

            # Color Wheel
            ui.label('Atmosphere Color').classes('text-xs font-bold opacity-50 mb-2')
            picker = ui.element('q-color').props('no-header no-footer default-view=spectrum format-model=hex class="full-width shadow-0"')
            picker.on('update:model-value', lambda e: on_color_change(e.args))
            
            # Footer Buttons (Inside scroll area at the bottom)
            with ui.row().classes('w-full justify-end mt-8 mb-4'):
                ui.button('Activate', on_click=activate_scene).props('flat')
                ui.button('Save Scene', on_click=save_custom_scene).props('flat color=green')

ui.run(title='Scene', port=8080)
