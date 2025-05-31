import tkinter as tk
from tkinter import ttk

# Import our own modules
from gui.gif_preview_window import GifPreviewWindow
from utils.utilities import Utilities

class OverrideSettingsWindow:
    """
    A window for overriding animation or spritesheet settings.

    This class creates a Tkinter window that allows the user to override settings such as FPS, delay, period, scale,
    threshold, indices, and frame-keeping options for a specific animation or spritesheet. The window is populated
    with current settings if available, and provides input fields for each configurable option.

    Attributes:
        window (tk.Toplevel): The Tkinter window instance.
        name (str): The name of the animation or spritesheet being configured.
        settings_type (str): Either "animation" or "spritesheet", indicating the type of settings to override.
        settings_manager: The settings manager instance used to retrieve and update settings.
        on_store_callback (callable): Callback function to call when the user confirms the changes.
        app: Reference to the main application instance.
        fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry (tk.Entry):
            Entry widgets for each configurable setting.

    Methods:
        store_input():
            Calls the provided callback with the current input values to store the overridden settings.
    """

    def __init__(self, window, name, settings_type, settings_manager, on_store_callback, app=None):
        self.window = window
        self.name = name
        self.settings_type = settings_type
        self.settings_manager = settings_manager
        self.on_store_callback = on_store_callback
        self.app = app

        local_settings = {}

        if settings_type == "animation":
            # For animation, use the full name as animation_name key (Ugly workaround for now)
            spritesheet_name = name.split("/", 1)[0] if "/" in name else name
            animation_name = name
            local_settings = self.settings_manager.animation_settings.get(animation_name, {})
        else:
            spritesheet_name = name
            animation_name = None
            local_settings = self.settings_manager.spritesheet_settings.get(spritesheet_name, {})

        settings = self.settings_manager.get_settings(spritesheet_name, animation_name)

        tk.Label(window, text="FPS for " + name).pack()
        self.fps_entry = tk.Entry(window)
        self.fps_entry.insert(0, str(local_settings.get('fps', '')))
        self.fps_entry.bind('<FocusIn>', lambda e: self.fps_entry.insert(0, settings.get('fps', '')) if (self.fps_entry.get() == '') else None)
        self.fps_entry.pack()

        tk.Label(window, text="Delay for " + name).pack()
        self.delay_entry = tk.Entry(window)
        self.delay_entry.insert(0, str(local_settings.get('delay', '')))
        self.delay_entry.bind('<FocusIn>', lambda e: self.delay_entry.insert(0, settings.get('delay', '')) if (self.delay_entry.get() == '') else None)
        self.delay_entry.pack()

        tk.Label(window, text="Min period for " + name).pack()
        self.period_entry = tk.Entry(window)
        self.period_entry.insert(0, str(local_settings.get('period', '')))
        self.period_entry.bind('<FocusIn>', lambda e: self.period_entry.insert(0, settings.get('period', '')) if (self.period_entry.get() == '') else None)
        self.period_entry.pack()

        tk.Label(window, text="Scale for " + name).pack()
        self.scale_entry = tk.Entry(window)
        self.scale_entry.insert(0, str(local_settings.get('scale', '')))
        self.scale_entry.bind('<FocusIn>', lambda e: self.scale_entry.insert(0, settings.get('scale', '')) if (self.scale_entry.get() == '') else None)
        self.scale_entry.pack()

        tk.Label(window, text="Threshold for " + name).pack()
        self.threshold_entry = tk.Entry(window)
        self.threshold_entry.insert(0, str(local_settings.get('threshold', '')))
        self.threshold_entry.bind('<FocusIn>', lambda e: self.threshold_entry.insert(0, settings.get('threshold', '')) if (self.threshold_entry.get() == '') else None)
        self.threshold_entry.pack()

        tk.Label(window, text="Indices for " + name).pack()
        self.indices_entry = tk.Entry(window)
        indices_val = local_settings.get('indices', '')
        if isinstance(indices_val, list):
            indices_val = ','.join(str(i) for i in indices_val)
        default_indices_val = settings.get('indices', '')
        if isinstance(default_indices_val, list):
            default_indices_val = ','.join(str(i) for i in default_indices_val)
        self.indices_entry.insert(0, str(indices_val))
        self.indices_entry.bind('<FocusIn>', lambda e: self.indices_entry.insert(0, default_indices_val) if (self.indices_entry.get() == '') else None)
        self.indices_entry.pack()

        tk.Label(window, text="Keep frames for " + name).pack()
        self.frames_var = tk.StringVar(value=str(local_settings.get('frames', '')))
        self.frames_entry = ttk.Combobox(window, textvariable=self.frames_var)
        self.frames_entry.bind('<FocusIn>', lambda e: self.frames_var.set(settings.get('frames', '')) if (self.frames_var.get() == '') else None)
        self.frames_entry['values'] = ("None", "All", "No duplicates", "First", "Last", "First, Last")
        self.frames_entry.pack()

        if settings_type == "animation":
            tk.Label(window, text="Filename for " + name).pack()
            self.filename_entry = tk.Entry(window)
            self.filename_entry.insert(0, local_settings.get('filename', ''))
            filename = str(Utilities.format_filename(
                    settings.get('prefix'),
                    spritesheet_name,
                    name.split("/", 1)[1],
                    settings.get('filename_format'),
                    settings.get('replace_rules')
                )
            )
            self.filename_entry.bind('<FocusIn>', lambda e: self.filename_entry.insert(0, filename) if (self.filename_entry.get() == '') else None)
            self.filename_entry.pack()

        tk.Button(window, text="OK", command=self.store_input).pack()
        
        if settings_type == "animation":
            tk.Button(window, text="Preview as GIF", command=lambda: GifPreviewWindow.preview(
                self.app, self.name, self.settings_type, 
                self.fps_entry, self.delay_entry, self.period_entry, 
                self.scale_entry, self.threshold_entry, self.indices_entry, self.frames_entry
            )).pack(pady=6)

    def store_input(self):
        if self.settings_type == "animation":
            self.on_store_callback(
                self.window, self.name, self.settings_type,
                self.fps_entry, self.delay_entry, self.period_entry,
                self.scale_entry, self.threshold_entry, self.indices_entry, self.frames_entry, self.filename_entry
            )
        else:
            self.on_store_callback(
                self.window, self.name, self.settings_type,
                self.fps_entry, self.delay_entry, self.period_entry,
                self.scale_entry, self.threshold_entry, self.indices_entry, self.frames_entry, None
            )