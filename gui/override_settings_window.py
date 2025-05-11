import tkinter as tk

class OverrideSettingsWindow:
    def __init__(self, window, name, settings_type, settings_manager, on_store_callback):
        self.window = window
        self.name = name
        self.settings_type = settings_type
        self.settings_manager = settings_manager
        self.on_store_callback = on_store_callback

        settings_map = {
            "animation": self.settings_manager.animation_settings,
            "spritesheet": self.settings_manager.spritesheet_settings,
        }
        settings = settings_map.get(settings_type, {}).get(name, {})

        tk.Label(window, text="FPS for " + name).pack()
        self.fps_entry = tk.Entry(window)
        if settings:
            self.fps_entry.insert(0, str(settings.get('fps', '')))
        self.fps_entry.pack()

        tk.Label(window, text="Delay for " + name).pack()
        self.delay_entry = tk.Entry(window)
        if settings:
            self.delay_entry.insert(0, str(settings.get('delay', '')))
        self.delay_entry.pack()

        tk.Label(window, text="Min period for " + name).pack()
        self.period_entry = tk.Entry(window)
        if settings:
            self.period_entry.insert(0, str(settings.get('period', '')))
        self.period_entry.pack()

        tk.Label(window, text="Scale for " + name).pack()
        self.scale_entry = tk.Entry(window)
        if settings:
            self.scale_entry.insert(0, str(settings.get('scale', '')))
        self.scale_entry.pack()

        tk.Label(window, text="Threshold for " + name).pack()
        self.threshold_entry = tk.Entry(window)
        if settings:
            self.threshold_entry.insert(0, str(settings.get('threshold', '')))
        self.threshold_entry.pack()

        tk.Label(window, text="Indices for " + name).pack()
        self.indices_entry = tk.Entry(window)
        if settings:
            self.indices_entry.insert(0, str(settings.get('indices', '')).translate(str.maketrans('', '', '[] ')))
        self.indices_entry.pack()

        tk.Label(window, text="Keep frames for " + name).pack()
        self.frames_entry = tk.Entry(window)
        if settings:
            self.frames_entry.insert(0, str(settings.get('frames', '')))
        self.frames_entry.pack()

        tk.Button(window, text="OK", command=self.store_input).pack()

    def store_input(self):
        self.on_store_callback(
            self.window, self.name, self.settings_type,
            self.fps_entry, self.delay_entry, self.period_entry,
            self.scale_entry, self.threshold_entry, self.indices_entry, self.frames_entry
        )