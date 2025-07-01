import tkinter as tk
from tkinter import ttk

# Import our own modules
from utils.utilities import Utilities


class OverrideSettingsWindow:
    """
    A window for overriding animation or spritesheet settings.

    This class creates a Tkinter window that allows the user to override settings such as animation format, FPS, delay,
    period, scale, threshold, indices, and frame-keeping options for a specific animation or spritesheet. The window is
    populated with current settings if available, and provides input fields for each configurable option.

    Attributes:
        window (tk.Toplevel): The Tkinter window instance.
        name (str): The name of the animation or spritesheet being configured.
        settings_type (str): Either "animation" or "spritesheet", indicating the type of settings to override.
        settings_manager: The settings manager instance used to retrieve and update settings.
        on_store_callback (callable): Callback function to call when the user confirms the changes.
        app: Reference to the main application instance.
        animation_format_entry (ttk.Combobox): Combobox for animation format selection.
        fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry (tk.Entry):
            Entry widgets for each configurable setting.
        frame_format_entry (ttk.Combobox): Combobox for frame format selection.
        frame_scale_entry (tk.Entry): Entry widget for frame scale setting.

    Methods:
        store_input():
            Calls the provided callback with the current input values to store the overridden settings.
    """

    def __init__(
        self, window, name, settings_type, settings_manager, on_store_callback, app=None
    ):
        self.window = window
        self.name = name
        self.settings_type = settings_type
        self.settings_manager = settings_manager
        self.on_store_callback = on_store_callback
        self.app = app

        # Set window title based on settings type
        title_prefix = "Animation" if settings_type == "animation" else "Spritesheet"
        self.window.title(f"{title_prefix} Settings Override - {name}")

        self.window.geometry("460x580")
        self.window.resizable(False, True)

        button_frame = tk.Frame(self.window, height=30)
        button_frame.pack(side="bottom", fill="x", pady=10, padx=10)
        button_frame.pack_propagate(False)

        button_container = tk.Frame(button_frame)
        button_container.place(relx=0.5, rely=0.5, anchor="center")

        ok_btn = tk.Button(
            button_container, text="OK", command=self.store_input, width=12
        )
        ok_btn.pack(side="left", padx=5)

        if settings_type == "animation":
            self.preview_btn = tk.Button(
                button_container,
                text="Preview animation",
                command=lambda: self.handle_preview_click(),
                width=15,
            )
            self.preview_btn.pack(side="left", padx=5)

        main_canvas = tk.Canvas(self.window, borderwidth=0, highlightthickness=0)
        main_scrollbar = tk.Scrollbar(
            self.window, orient="vertical", command=main_canvas.yview
        )
        main_canvas.configure(yscrollcommand=main_scrollbar.set)

        main_frame = tk.Frame(main_canvas)
        main_canvas_window = main_canvas.create_window(
            (0, 0), window=main_frame, anchor="nw"
        )

        def _on_main_frame_configure(event):
            main_canvas.configure(scrollregion=main_canvas.bbox("all"))

        main_frame.bind("<Configure>", _on_main_frame_configure)

        def _on_main_canvas_configure(event):
            canvas_width = event.width
            main_canvas.itemconfig(main_canvas_window, width=canvas_width)

        main_canvas.bind("<Configure>", _on_main_canvas_configure)

        def _on_main_mousewheel(event):
            main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_main_linux_scroll(event):
            if event.num == 4:
                main_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                main_canvas.yview_scroll(1, "units")

        def _on_key_scroll(event):
            if event.keysym == "Up":
                main_canvas.yview_scroll(-1, "units")
            elif event.keysym == "Down":
                main_canvas.yview_scroll(1, "units")
            elif event.keysym == "Prior":  # Page Up
                main_canvas.yview_scroll(-5, "units")
            elif event.keysym == "Next":  # Page Down
                main_canvas.yview_scroll(5, "units")
            elif event.keysym == "Home":
                main_canvas.yview_moveto(0)
            elif event.keysym == "End":
                main_canvas.yview_moveto(1)

        try:
            import platform

            if platform.system() == "Windows" or platform.system() == "Darwin":
                main_canvas.bind("<MouseWheel>", _on_main_mousewheel)
            elif platform.system() == "Linux":
                main_canvas.bind("<Button-4>", _on_main_linux_scroll)
                main_canvas.bind("<Button-5>", _on_main_linux_scroll)
        except ImportError:
            main_canvas.bind("<MouseWheel>", _on_main_mousewheel)

        self.window.bind("<Key>", _on_key_scroll)
        self.window.focus_set()

        main_canvas.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=8)
        main_scrollbar.pack(side="right", fill="y", pady=8)

        content_frame = tk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True, padx=(0, 12))

        local_settings = {}

        if settings_type == "animation":
            # For animation, use the full name as animation_name key (Ugly workaround for now)
            spritesheet_name = name.split("/", 1)[0] if "/" in name else name
            animation_name = name
            local_settings = self.settings_manager.animation_settings.get(
                animation_name, {}
            )
        else:
            spritesheet_name = name
            animation_name = None
            local_settings = self.settings_manager.spritesheet_settings.get(
                spritesheet_name, {}
            )

        settings = self.settings_manager.get_settings(spritesheet_name, animation_name)

        content_frame.grid_columnconfigure(0, weight=1)

        row = 0

        mode_text = (
            "Animation Settings Override"
            if settings_type == "animation"
            else "Spritesheet Settings Override"
        )
        mode_label = tk.Label(
            content_frame,
            text=mode_text,
            font=("Arial", 12, "bold"),
            fg="#333333",
        )
        mode_label.grid(row=row, column=0, sticky="w", pady=(0, 12))
        row += 1

        # General export settings section
        tk.Label(
            content_frame, text="General export settings", font=("Arial", 10, "bold")
        ).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1

        general_outer_frame = tk.Frame(
            content_frame,
            borderwidth=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground="#888",
        )
        general_outer_frame.grid(
            row=row, column=0, sticky="ew", padx=(0, 0), pady=(0, 10)
        )
        general_outer_frame.grid_columnconfigure(0, weight=1)

        general_frame = tk.Frame(general_outer_frame, padx=8, pady=8)
        general_frame.grid(row=0, column=0, sticky="ew")
        general_frame.grid_columnconfigure(0, weight=1)
        general_frame.grid_columnconfigure(1, weight=1)

        general_row = 0

        tk.Label(general_frame, text="Name:").grid(
            row=general_row, column=0, sticky="w", pady=2
        )
        name_label = tk.Label(general_frame, text=name, wraplength=200, justify="left")
        name_label.grid(row=general_row, column=1, sticky="w", padx=(8, 0), pady=2)
        general_row += 1

        if settings_type == "animation" and "/" in name:
            tk.Label(general_frame, text="Spritesheet:").grid(
                row=general_row, column=0, sticky="w", pady=2
            )
            parent_label = tk.Label(
                general_frame, text=spritesheet_name, wraplength=200, justify="left"
            )
            parent_label.grid(
                row=general_row, column=1, sticky="w", padx=(8, 0), pady=2
            )
            general_row += 1

        if settings_type == "animation":
            tk.Label(general_frame, text="Filename:").grid(
                row=general_row, column=0, sticky="w", pady=2
            )
            self.filename_entry = tk.Entry(general_frame, width=20)
            self.filename_entry.insert(0, local_settings.get("filename", ""))
            filename = str(
                Utilities.format_filename(
                    settings.get("prefix"),
                    spritesheet_name,
                    name.split("/", 1)[1] if "/" in name else "",
                    settings.get("filename_format"),
                    settings.get("replace_rules"),
                )
            )
            self.filename_entry.bind(
                "<FocusIn>",
                lambda e: (
                    self.filename_entry.insert(0, filename)
                    if (self.filename_entry and self.filename_entry.get() == "")
                    else None
                ),
            )
            self.filename_entry.grid(
                row=general_row, column=1, sticky="ew", padx=(8, 0), pady=2
            )
            general_row += 1
        else:
            self.filename_entry = None

        row += 1

        # Animation export settings section
        section_title = "Animation export settings"
        tk.Label(content_frame, text=section_title, font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=(0, 4)
        )
        row += 1

        anim_outer_frame = tk.Frame(
            content_frame,
            borderwidth=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground="#888",
        )
        anim_outer_frame.grid(row=row, column=0, sticky="ew", padx=(0, 0), pady=(0, 10))
        anim_outer_frame.grid_columnconfigure(0, weight=1)

        anim_frame = tk.Frame(anim_outer_frame, padx=8, pady=8)
        anim_frame.grid(row=0, column=0, sticky="ew")
        anim_frame.grid_columnconfigure(0, weight=1)
        anim_frame.grid_columnconfigure(1, weight=1)

        anim_row = 0

        tk.Label(anim_frame, text="Animation format:").grid(
            row=anim_row, column=0, sticky="w", pady=2
        )
        self.animation_format_var = tk.StringVar(
            value=str(local_settings.get("animation_format", ""))
        )
        self.animation_format_entry = ttk.Combobox(
            anim_frame,
            textvariable=self.animation_format_var,
            state="readonly",
            width=18,
        )
        self.animation_format_entry.bind(
            "<FocusIn>",
            lambda e: self.animation_format_var.set(
                settings.get("animation_format", "")
            )
            if (self.animation_format_var.get() == "")
            else None,
        )
        self.animation_format_entry.bind(
            "<<ComboboxSelected>>", self.on_animation_format_change
        )
        self.animation_format_entry["values"] = (
            "None",
            "GIF",
            "WebP",
            "APNG",
        )
        self.animation_format_entry.grid(
            row=anim_row, column=1, sticky="ew", padx=(8, 0), pady=2
        )
        anim_row += 1

        tk.Label(anim_frame, text="FPS:").grid(
            row=anim_row, column=0, sticky="w", pady=2
        )
        self.fps_entry = tk.Entry(anim_frame, width=20)
        self.fps_entry.insert(0, str(local_settings.get("fps", "")))
        self.fps_entry.bind(
            "<FocusIn>",
            lambda e: self.fps_entry.insert(0, settings.get("fps", ""))
            if (self.fps_entry.get() == "")
            else None,
        )
        self.fps_entry.grid(row=anim_row, column=1, sticky="ew", padx=(8, 0), pady=2)
        anim_row += 1

        tk.Label(anim_frame, text="Delay (ms):").grid(
            row=anim_row, column=0, sticky="w", pady=2
        )
        self.delay_entry = tk.Entry(anim_frame, width=20)
        self.delay_entry.insert(0, str(local_settings.get("delay", "")))
        self.delay_entry.bind(
            "<FocusIn>",
            lambda e: self.delay_entry.insert(0, settings.get("delay", ""))
            if (self.delay_entry.get() == "")
            else None,
        )
        self.delay_entry.grid(row=anim_row, column=1, sticky="ew", padx=(8, 0), pady=2)
        anim_row += 1

        tk.Label(anim_frame, text="Min period (ms):").grid(
            row=anim_row, column=0, sticky="w", pady=2
        )
        self.period_entry = tk.Entry(anim_frame, width=20)
        self.period_entry.insert(0, str(local_settings.get("period", "")))
        self.period_entry.bind(
            "<FocusIn>",
            lambda e: self.period_entry.insert(0, settings.get("period", ""))
            if (self.period_entry.get() == "")
            else None,
        )
        self.period_entry.grid(row=anim_row, column=1, sticky="ew", padx=(8, 0), pady=2)
        anim_row += 1

        tk.Label(anim_frame, text="Scale:").grid(
            row=anim_row, column=0, sticky="w", pady=2
        )
        self.scale_entry = tk.Entry(anim_frame, width=20)
        self.scale_entry.insert(0, str(local_settings.get("scale", "")))
        self.scale_entry.bind(
            "<FocusIn>",
            lambda e: self.scale_entry.insert(0, settings.get("scale", ""))
            if (self.scale_entry.get() == "")
            else None,
        )
        self.scale_entry.grid(row=anim_row, column=1, sticky="ew", padx=(8, 0), pady=2)
        anim_row += 1

        tk.Label(anim_frame, text="Threshold:").grid(
            row=anim_row, column=0, sticky="w", pady=2
        )
        self.threshold_entry = tk.Entry(anim_frame, width=20)
        self.threshold_entry.insert(0, str(local_settings.get("threshold", "")))
        self.threshold_entry.bind(
            "<FocusIn>",
            lambda e: self.threshold_entry.insert(0, settings.get("threshold", ""))
            if (self.threshold_entry.get() == "")
            else None,
        )
        self.threshold_entry.grid(
            row=anim_row, column=1, sticky="ew", padx=(8, 0), pady=2
        )
        anim_row += 1

        if settings_type == "animation":
            tk.Label(anim_frame, text="Indices:").grid(
                row=anim_row, column=0, sticky="w", pady=2
            )
            self.indices_entry = tk.Entry(anim_frame, width=20)
            indices_val = local_settings.get("indices", "")
            if isinstance(indices_val, list):
                indices_val = ",".join(str(i) for i in indices_val)
            default_indices_val = settings.get("indices", "")
            if isinstance(default_indices_val, list):
                default_indices_val = ",".join(str(i) for i in default_indices_val)
            self.indices_entry.insert(0, str(indices_val))
            self.indices_entry.bind(
                "<FocusIn>",
                lambda e: self.indices_entry.insert(0, default_indices_val)
                if (self.indices_entry.get() == "")
                else None,
            )
            self.indices_entry.grid(
                row=anim_row, column=1, sticky="ew", padx=(8, 0), pady=2
            )
            anim_row += 1
        else:
            # For spritesheet override settings, create a hidden entry to maintain compatibility
            self.indices_entry = tk.Entry(content_frame)
            indices_val = local_settings.get("indices", "")
            if isinstance(indices_val, list):
                indices_val = ",".join(str(i) for i in indices_val)
            self.indices_entry.insert(0, str(indices_val))

        row += 1

        # Frame export settings section
        tk.Label(
            content_frame, text="Frame export settings", font=("Arial", 10, "bold")
        ).grid(row=row, column=0, sticky="w", pady=(8, 4))
        row += 1

        frame_outer_frame = tk.Frame(
            content_frame,
            borderwidth=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground="#888",
        )
        frame_outer_frame.grid(
            row=row, column=0, sticky="ew", padx=(0, 0), pady=(0, 10)
        )
        frame_outer_frame.grid_columnconfigure(0, weight=1)

        frame_frame = tk.Frame(frame_outer_frame, padx=8, pady=8)
        frame_frame.grid(row=0, column=0, sticky="ew")
        frame_frame.grid_columnconfigure(0, weight=1)
        frame_frame.grid_columnconfigure(1, weight=1)

        frame_row = 0

        tk.Label(frame_frame, text="Frame selection:").grid(
            row=frame_row, column=0, sticky="w", pady=2
        )
        self.frames_var = tk.StringVar(
            value=str(local_settings.get("frame_selection", ""))
        )
        self.frames_entry = ttk.Combobox(
            frame_frame, textvariable=self.frames_var, width=18
        )
        self.frames_entry.bind(
            "<FocusIn>",
            lambda e: self.frames_var.set(settings.get("frame_selection", ""))
            if (self.frames_var.get() == "")
            else None,
        )
        self.frames_entry["values"] = (
            "All",
            "No duplicates",
            "First",
            "Last",
            "First, Last",
        )
        self.frames_entry.grid(
            row=frame_row, column=1, sticky="ew", padx=(8, 0), pady=2
        )
        frame_row += 1

        tk.Label(frame_frame, text="Frame format:").grid(
            row=frame_row, column=0, sticky="w", pady=2
        )
        self.frame_format_var = tk.StringVar(
            value=str(local_settings.get("frame_format", ""))
        )
        self.frame_format_entry = ttk.Combobox(
            frame_frame, textvariable=self.frame_format_var, state="readonly", width=18
        )
        self.frame_format_entry.bind(
            "<FocusIn>",
            lambda e: self.frame_format_var.set(settings.get("frame_format", ""))
            if (self.frame_format_var.get() == "")
            else None,
        )
        self.frame_format_entry["values"] = (
            "None",
            "AVIF",
            "BMP",
            "DDS",
            "PNG",
            "TGA",
            "TIFF",
            "WebP",
        )
        self.frame_format_entry.grid(
            row=frame_row, column=1, sticky="ew", padx=(8, 0), pady=2
        )
        frame_row += 1

        tk.Label(frame_frame, text="Frame scale:").grid(
            row=frame_row, column=0, sticky="w", pady=2
        )
        self.frame_scale_entry = tk.Entry(frame_frame, width=20)
        self.frame_scale_entry.insert(0, str(local_settings.get("frame_scale", "")))
        self.frame_scale_entry.bind(
            "<FocusIn>",
            lambda e: self.frame_scale_entry.insert(
                0, str(settings.get("frame_scale", ""))
            )
            if (self.frame_scale_entry.get() == "")
            else None,
        )
        self.frame_scale_entry.grid(
            row=frame_row, column=1, sticky="ew", padx=(8, 0), pady=2
        )

        if settings_type == "animation":
            self.on_animation_format_change()

    def store_input(self):
        if self.settings_type == "animation":
            self.on_store_callback(
                self.window,
                self.name,
                self.settings_type,
                self.animation_format_entry,
                self.fps_entry,
                self.delay_entry,
                self.period_entry,
                self.scale_entry,
                self.threshold_entry,
                self.indices_entry,
                self.frames_entry,
                self.filename_entry,
                self.frame_format_entry,
                self.frame_scale_entry,
            )
        else:
            self.on_store_callback(
                self.window,
                self.name,
                self.settings_type,
                self.animation_format_entry,
                self.fps_entry,
                self.delay_entry,
                self.period_entry,
                self.scale_entry,
                self.threshold_entry,
                self.indices_entry,
                self.frames_entry,
                None,  # No filename entry for spritesheets
                self.frame_format_entry,
                self.frame_scale_entry,
            )

    def handle_preview_click(self):
        from tkinter import messagebox
        from gui.animation_preview_window import AnimationPreviewWindow

        animation_format = self.animation_format_entry.get()
        if animation_format == "APNG":
            messagebox.showinfo(
                "Preview Not Available",
                "Preview is not available for APNG format due to display limitations.\n\n"
                "You can still export APNG animations and view them externally.",
            )
            return

        AnimationPreviewWindow.preview(
            self.app,
            self.name,
            self.settings_type,
            self.animation_format_entry,
            self.fps_entry,
            self.delay_entry,
            self.period_entry,
            self.scale_entry,
            self.threshold_entry,
            self.indices_entry,
            self.frames_entry,
        )

    def on_animation_format_change(self, event=None):
        if hasattr(self, "preview_btn"):
            animation_format = self.animation_format_entry.get()
            self.preview_btn.config(
                text=f"Preview as {animation_format}", state="normal"
            )
