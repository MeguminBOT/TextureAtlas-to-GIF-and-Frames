import tkinter as tk

class SettingsWindow:
    def __init__(self, parent, settings_manager):
        self.settings_window = tk.Toplevel(parent)
        self.settings_window.geometry("400x300")
        settings_canvas = tk.Canvas(self.settings_window)
        settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        settings_scrollbar = tk.Scrollbar(self.settings_window, orient=tk.VERTICAL, command=settings_canvas.yview)
        settings_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        settings_canvas.config(yscrollcommand=settings_scrollbar.set)
        settings_frame = tk.Frame(settings_canvas)
        settings_canvas.create_window((0, 0), window=settings_frame, anchor=tk.NW)
        self.update_settings_window(settings_frame, settings_canvas, settings_manager)
        settings_frame.update_idletasks()
        settings_canvas.config(scrollregion=settings_canvas.bbox("all"))

    def update_settings_window(self, settings_frame, settings_canvas, settings_manager):
        for widget in settings_frame.winfo_children():
            widget.destroy()

        tk.Label(settings_frame, text="Animation Settings").pack(pady=10)
        for key, value in settings_manager.animation_settings.items():
            tk.Label(settings_frame, text=f"{key}: {value}").pack(anchor=tk.W, padx=20)

        tk.Label(settings_frame, text="Spritesheet Settings").pack(pady=10)
        for key, value in settings_manager.spritesheet_settings.items():
            tk.Label(settings_frame, text=f"{key}: {value}").pack(anchor=tk.W, padx=20)

        settings_frame.update_idletasks()
        settings_canvas.config(scrollregion=settings_canvas.bbox("all"))