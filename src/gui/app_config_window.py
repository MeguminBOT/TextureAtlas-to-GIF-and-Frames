import tkinter as tk
from tkinter import messagebox
import psutil
import multiprocessing
import platform
import subprocess

# Import our own modules
from core.exception_handler import ExceptionHandler


class AppConfigWindow:
    """
    A scrollable window for configuring application settings.

    This window provides a comprehensive interface for configuring various application
    settings including resource limits, extraction defaults, compression defaults,
    update preferences, and UI options. The window is fully scrollable to accommodate
    growing settings and includes keyboard navigation.

    Attributes:
        window (tk.Toplevel): The options window instance.
        app_config: The application's configuration object (AppConfig).
        max_cores (int): Number of logical CPU cores available.
        max_threads (int): Number of logical CPU threads available (may be same as max_cores).
        max_memory_mb (int): Total physical RAM in megabytes.
        cpu_var (tk.StringVar): Tkinter variable for CPU threads input field.
        mem_var (tk.StringVar): Tkinter variable for memory limit input field.
        extraction_fields (dict): Dictionary of extraction settings fields and their types.
        extraction_vars (dict): Dictionary of Tkinter variables for extraction settings.
        compression_vars (dict): Dictionary of Tkinter variables for compression settings.
        check_updates_var (tk.BooleanVar): Tkinter variable for the 'Check for updates on startup' checkbox.
        auto_update_var (tk.BooleanVar): Tkinter variable for the 'Auto-download and install updates' checkbox.

    Methods:
        __init__(parent, app_config):
            Initialize the scrollable options window with system information and current settings.
        _on_extraction_frame_configure(event):
            Configure the extraction frame to adjust its scroll region.
        _on_canvas_configure(event):
            Configure the canvas to adjust its width based on the window size.
        _on_mousewheel(event):
            Handle mouse wheel scrolling for the extraction canvas.
        _on_linux_scroll(event):
            Handle mouse scroll events on Linux systems.
        reset_to_defaults():
            Reset all fields to the application's initial defaults.
        save_config():
            Validate and save user settings to the app config.
        parse_value(key, val, expected_type):
            Static method to parse and validate a value based on its expected type, raising errors for invalid inputs.

    Keyboard Navigation:
        Arrow Keys: Scroll up/down
        Page Up/Down: Scroll by larger increments
        Home/End: Jump to top/bottom of settings
        Mouse Wheel: Scroll up/down (works anywhere in window)
    """

    def __init__(self, parent, app_config):
        self.window = tk.Toplevel(parent)
        self.window.title("App options")
        self.window.geometry("480x700")
        self.window.resizable(False, False)
        self.app_config = app_config

        # Create button frame FIRST to reserve space at bottom
        button_frame = tk.Frame(self.window, height=60)
        button_frame.pack(side="bottom", fill="x", pady=10, padx=20)
        button_frame.pack_propagate(False)  # Maintain fixed height

        button_container = tk.Frame(button_frame)
        button_container.place(relx=0.5, rely=0.5, anchor="center")

        save_btn = tk.Button(button_container, text="Save", command=self.save_config, width=12)
        save_btn.pack(side="left", padx=5)

        cancel_btn = tk.Button(button_container, text="Cancel", command=self.window.destroy, width=12)
        cancel_btn.pack(side="left", padx=5)

        reset_btn = tk.Button(button_container, text="Reset to defaults", command=self.reset_to_defaults, width=18)
        reset_btn.pack(side="left", padx=5)
        main_canvas = tk.Canvas(self.window, borderwidth=0, highlightthickness=0)
        main_scrollbar = tk.Scrollbar(self.window, orient="vertical", command=main_canvas.yview)
        main_canvas.configure(yscrollcommand=main_scrollbar.set)

        main_frame = tk.Frame(main_canvas)
        main_canvas_window = main_canvas.create_window((0, 0), window=main_frame, anchor="nw")

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
            elif event.keysym == "Page_Up":
                main_canvas.yview_scroll(-5, "units")
            elif event.keysym == "Page_Down":
                main_canvas.yview_scroll(5, "units")
            elif event.keysym == "Home":
                main_canvas.yview_moveto(0)
            elif event.keysym == "End":
                main_canvas.yview_moveto(1)

        if platform.system() == "Windows" or platform.system() == "Darwin":
            main_canvas.bind("<MouseWheel>", _on_main_mousewheel)
            self.window.bind("<MouseWheel>", _on_main_mousewheel)
        elif platform.system() == "Linux":
            main_canvas.bind("<Button-4>", _on_main_linux_scroll)
            main_canvas.bind("<Button-5>", _on_main_linux_scroll)
            self.window.bind("<Button-4>", _on_main_linux_scroll)
            self.window.bind("<Button-5>", _on_main_linux_scroll)

        self.window.bind("<Key>", _on_key_scroll)
        self.window.focus_set()

        main_canvas.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=8)
        main_scrollbar.pack(side="right", fill="y", pady=8)
        content_frame = tk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True, padx=(0, 12))

        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        self.max_cores = multiprocessing.cpu_count()
        self.max_threads = None
        self.max_memory_mb = int(psutil.virtual_memory().total / (1024 * 1024))

        cpu_model = "Unknown CPU"
        try:
            if platform.system() == "Windows":
                cpu_model = subprocess.check_output(
                    'wmic cpu get Name', shell=True
                ).decode(errors='ignore').split('\n')[1].strip()
                self.max_threads = int(
                    subprocess.check_output(
                        'wmic cpu get NumberOfLogicalProcessors', shell=True
                    ).decode(errors='ignore').split('\n')[1].strip()
                )

            elif platform.system() == "Linux":
                with open('/proc/cpuinfo') as f:
                    for line in f:
                        if 'model name' in line:
                            cpu_model = line.split(':')[1].strip()
                        if 'processor' in line:
                            if self.max_threads is None:
                                self.max_threads = 0
                            self.max_threads += 1

            elif platform.system() == "Darwin":
                cpu_model = subprocess.check_output(
                    ['sysctl', '-n', 'machdep.cpu.brand_string']
                ).decode(errors='ignore').strip()
                self.max_threads = int(
                    subprocess.check_output(
                        ['sysctl', '-n', 'hw.logicalcpu']
                    ).decode(errors='ignore').strip()
                )
        except Exception:
            pass

        if not self.max_threads:
            self.max_threads = self.max_cores

        row = 0
        tk.Label(content_frame, text="Your computer", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(0, 2), columnspan=2)
        row += 1
        tk.Label(content_frame, text=f"CPU: {cpu_model} (Threads: {self.max_threads})", font=("Arial", 9)).grid(row=row, column=0, sticky="w", columnspan=2)
        row += 1
        tk.Label(content_frame, text=f"RAM: {self.max_memory_mb:,} MB", font=("Arial", 9)).grid(row=row, column=0, sticky="w", pady=(0, 8), columnspan=2)
        row += 1

        tk.Label(content_frame, text="App resource limits", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(0, 4), columnspan=2)
        row += 1
        resource_canvas = tk.Canvas(content_frame, borderwidth=1, relief="solid", highlightthickness=1, highlightbackground="#888")
        resource_canvas.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8), padx=(0, 0))
        resource_frame = tk.Frame(resource_canvas, padx=4, pady=4)

        resource_frame.grid_columnconfigure(0, weight=1)
        resource_frame.grid_columnconfigure(1, weight=0)

        tk.Label(resource_frame, text=f"CPU threads to use (max: {self.max_threads}):").grid(row=0, column=0, sticky="w")
        resource_limits = self.app_config.get("resource_limits", {})
        default_threads = (self.max_threads + 1) // 4

        cpu_default = resource_limits.get("cpu_cores", "auto")
        if cpu_default is None or cpu_default == "auto":
            cpu_default = str(default_threads)

        self.cpu_var = tk.StringVar(value=str(cpu_default))
        self.cpu_entry = tk.Entry(resource_frame, textvariable=self.cpu_var, width=10)
        self.cpu_entry.grid(row=0, column=1, sticky="w", padx=(8, 0))

        # Memory limit is not actually implemented in the app yet as it requires vast code changes but we add it for future use
        tk.Label(resource_frame, text=f"Memory limit (MB, max: {self.max_memory_mb}):").grid(row=1, column=0, sticky="w", pady=(4, 0))
        default_mem = ((self.max_memory_mb // 4 + 9) // 10) * 10
        mem_default = resource_limits.get("memory_limit_mb", 0)

        if mem_default is None or mem_default == 0:
            mem_default = str(default_mem)

        self.mem_var = tk.StringVar(value=str(mem_default))
        self.mem_entry = tk.Entry(resource_frame, textvariable=self.mem_var, width=10, state="disabled")  # Disabled until implemented
        self.mem_entry.grid(row=1, column=1, sticky="w", padx=(8, 0))

        resource_frame.update_idletasks()
        req_width = resource_frame.winfo_reqwidth() + 3
        req_height = resource_frame.winfo_reqheight() + 3
        resource_canvas.configure(width=req_width, height=req_height)
        resource_canvas.update_idletasks()
        resource_canvas.yview_moveto(0)
        resource_canvas.xview_moveto(0)
        resource_canvas.create_window((0, 0), window=resource_frame, anchor="nw")

        row += 1
        tk.Label(content_frame, text="Extraction defaults", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(16, 2), columnspan=2)
        row += 1
        defaults = self.app_config.get_extraction_defaults() if hasattr(self.app_config, 'get_extraction_defaults') else {}

        resource_frame.update_idletasks()

        extraction_outer_frame = tk.Frame(content_frame, borderwidth=1, relief="solid", highlightthickness=1, highlightbackground="#888")
        extraction_outer_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=(0, 0), pady=(0, 10))

        content_frame.grid_columnconfigure(0, weight=1)
        extraction_outer_frame.grid_columnconfigure(0, weight=1)

        extraction_canvas = tk.Canvas(extraction_outer_frame, borderwidth=0, highlightthickness=0)
        extraction_canvas.grid(row=0, column=0, sticky="ew")

        extraction_scrollbar = tk.Scrollbar(extraction_outer_frame, orient="vertical", command=extraction_canvas.yview)
        extraction_scrollbar.grid(row=0, column=1, sticky="ns")
        extraction_canvas.configure(yscrollcommand=extraction_scrollbar.set)

        extraction_frame = tk.Frame(extraction_canvas, padx=4, pady=4)
        canvas_window = extraction_canvas.create_window((0, 0), window=extraction_frame, anchor="nw")

        extraction_frame.grid_columnconfigure(0, weight=1)
        extraction_frame.grid_columnconfigure(1, weight=0)  # For labels
        extraction_frame.grid_columnconfigure(2, weight=1)  # For entry/combobox widgets

        def _on_extraction_frame_configure(event):
            extraction_canvas.configure(scrollregion=extraction_canvas.bbox("all"))
        extraction_frame.bind("<Configure>", _on_extraction_frame_configure)

        def _on_canvas_configure(event):
            canvas_width = event.width
            extraction_canvas.itemconfig(canvas_window, width=canvas_width)
        extraction_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            extraction_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_linux_scroll(event):
            if event.num == 4:
                extraction_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                extraction_canvas.yview_scroll(1, "units")

        if platform.system() == "Windows" or platform.system() == "Darwin":
            extraction_canvas.bind("<MouseWheel>", _on_mousewheel)
        elif platform.system() == "Linux":
            extraction_canvas.bind("<Button-4>", _on_linux_scroll)
            extraction_canvas.bind("<Button-5>", _on_linux_scroll)

        self.extraction_fields = {
            "animation_format": (tk.StringVar, ["None", "GIF", "WebP", "APNG"]),
            "fps": (tk.StringVar, None),
            "delay": (tk.StringVar, None),
            "period": (tk.StringVar, None),
            "scale": (tk.StringVar, None),
            "threshold": (tk.StringVar, None),
            "crop_option": (tk.StringVar, ["None", "Animation based", "Frame based"]),
            "frame_format": (tk.StringVar, ["None", "AVIF", "BMP", "DDS", "PNG", "TGA", "TIFF", "WebP"]),
            "frame_scale": (tk.StringVar, None),
            "frame_selection": (tk.StringVar, ["All", "No duplicates", "First", "Last", "First, Last"]),
            "filename_format": (tk.StringVar, ["Standardized", "No spaces", "No special characters"]),
            "variable_delay": (tk.BooleanVar, None),
            "fnf_idle_loop": (tk.BooleanVar, None),
        }

        self.extraction_vars = {}
        option_row = 0
        for key, (var_type, options) in self.extraction_fields.items():
            label = key.replace("_", " ").capitalize() + (":" if not key.startswith("fnf") else " (sets loop delay to 0):")
            tk.Label(extraction_frame, text=label).grid(row=option_row, column=0, sticky="w")
            default_val = defaults.get(key, "" if var_type is tk.StringVar else False)
            if var_type is tk.BooleanVar:
                self.extraction_vars[key] = var_type(value=default_val)
                tk.Checkbutton(extraction_frame, variable=self.extraction_vars[key]).grid(row=option_row, column=1, sticky="w", padx=(8, 0))
            elif options:
                self.extraction_vars[key] = var_type(value=default_val)
                tk.OptionMenu(extraction_frame, self.extraction_vars[key], *options).grid(row=option_row, column=1, sticky="w", padx=(8, 0))
            else:
                self.extraction_vars[key] = var_type(value=str(default_val))
                tk.Entry(extraction_frame, textvariable=self.extraction_vars[key], width=10).grid(row=option_row, column=1, sticky="w", padx=(8, 0))
            option_row += 1

        row += 1
        tk.Label(content_frame, text="Update settings", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(8, 2), columnspan=2)
        row += 1

        update_outer_frame = tk.Frame(content_frame, borderwidth=1, relief="solid", highlightthickness=1, highlightbackground="#888")
        update_outer_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=(0, 0), pady=(0, 10))

        update_settings = self.app_config.get("update_settings", self.app_config.DEFAULTS["update_settings"])
        self.check_updates_var = tk.BooleanVar(value=update_settings.get("check_updates_on_startup", True))
        self.auto_update_var = tk.BooleanVar(value=update_settings.get("auto_download_updates", False))

        def on_check_updates_change(*args):
            if not self.check_updates_var.get():
                self.auto_update_var.set(False)
                self.auto_update_cb.config(state="disabled")
            else:
                self.auto_update_cb.config(state="normal")

        self.check_updates_cb = tk.Checkbutton(update_outer_frame, text="Check for updates on startup", variable=self.check_updates_var)
        self.check_updates_cb.pack(anchor="w", padx=4, pady=(4, 0))
        self.auto_update_cb = tk.Checkbutton(update_outer_frame, text="Auto-download and install updates", variable=self.auto_update_var)
        self.auto_update_cb.pack(anchor="w", padx=4, pady=(0, 4))

        self.check_updates_var.trace_add('write', lambda *args: on_check_updates_change())
        on_check_updates_change()

        row += 1
        tk.Label(content_frame, text="Compression defaults", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(16, 2), columnspan=2)
        row += 1

        compression_outer_frame = tk.Frame(content_frame, borderwidth=1, relief="solid", highlightthickness=1, highlightbackground="#888")
        compression_outer_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=(0, 0), pady=(0, 10))

        content_frame.grid_columnconfigure(0, weight=1)
        compression_outer_frame.grid_columnconfigure(0, weight=1)

        compression_canvas = tk.Canvas(compression_outer_frame, borderwidth=0, highlightthickness=0)
        compression_canvas.grid(row=0, column=0, sticky="ew")

        compression_scrollbar = tk.Scrollbar(compression_outer_frame, orient="vertical", command=compression_canvas.yview)
        compression_scrollbar.grid(row=0, column=1, sticky="ns")
        compression_canvas.configure(yscrollcommand=compression_scrollbar.set)

        compression_frame = tk.Frame(compression_canvas, padx=4, pady=4)
        compression_canvas_window = compression_canvas.create_window((0, 0), window=compression_frame, anchor="nw")

        compression_frame.grid_columnconfigure(0, weight=1)
        compression_frame.grid_columnconfigure(1, weight=0)
        compression_frame.grid_columnconfigure(2, weight=1)

        def _on_compression_frame_configure(event):
            compression_canvas.configure(scrollregion=compression_canvas.bbox("all"))
        compression_frame.bind("<Configure>", _on_compression_frame_configure)

        def _on_compression_canvas_configure(event):
            canvas_width = event.width
            compression_canvas.itemconfig(compression_canvas_window, width=canvas_width)
        compression_canvas.bind("<Configure>", _on_compression_canvas_configure)

        def _on_compression_mousewheel(event):
            compression_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_compression_linux_scroll(event):
            if event.num == 4:
                compression_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                compression_canvas.yview_scroll(1, "units")

        if platform.system() == "Windows" or platform.system() == "Darwin":
            compression_canvas.bind("<MouseWheel>", _on_compression_mousewheel)
        elif platform.system() == "Linux":
            compression_canvas.bind("<Button-4>", _on_compression_linux_scroll)
            compression_canvas.bind("<Button-5>", _on_compression_linux_scroll)

        compression_defaults = self.app_config.get_compression_defaults()
        self.compression_vars = {}

        comp_row = 0

        tk.Label(compression_frame, text="PNG Settings", font=("Arial", 9, "bold")).grid(row=comp_row, column=0, columnspan=3, sticky="w", pady=(4, 2))
        comp_row += 1

        tk.Label(compression_frame, text="Compress level (0-9):").grid(row=comp_row, column=0, sticky="w")
        self.compression_vars['png_compress_level'] = tk.IntVar(value=compression_defaults.get('png', {}).get('compress_level', 9))
        tk.Spinbox(compression_frame, from_=0, to=9, textvariable=self.compression_vars['png_compress_level'], width=10).grid(row=comp_row, column=1, sticky="w", padx=(8, 0))
        comp_row += 1

        self.compression_vars['png_optimize'] = tk.BooleanVar(value=compression_defaults.get('png', {}).get('optimize', True))
        tk.Checkbutton(compression_frame, text="Optimize PNG", variable=self.compression_vars['png_optimize']).grid(row=comp_row, column=0, columnspan=2, sticky="w")
        comp_row += 1

        tk.Label(compression_frame, text="WebP Settings", font=("Arial", 9, "bold")).grid(row=comp_row, column=0, columnspan=3, sticky="w", pady=(12, 2))
        comp_row += 1

        self.compression_vars['webp_lossless'] = tk.BooleanVar(value=compression_defaults.get('webp', {}).get('lossless', True))
        tk.Checkbutton(compression_frame, text="Lossless WebP", variable=self.compression_vars['webp_lossless']).grid(row=comp_row, column=0, columnspan=2, sticky="w")
        comp_row += 1

        tk.Label(compression_frame, text="Quality (0-100):").grid(row=comp_row, column=0, sticky="w")
        self.compression_vars['webp_quality'] = tk.IntVar(value=compression_defaults.get('webp', {}).get('quality', 100))
        tk.Spinbox(compression_frame, from_=0, to=100, textvariable=self.compression_vars['webp_quality'], width=10).grid(row=comp_row, column=1, sticky="w", padx=(8, 0))
        comp_row += 1

        tk.Label(compression_frame, text="Method (0-6):").grid(row=comp_row, column=0, sticky="w")
        self.compression_vars['webp_method'] = tk.IntVar(value=compression_defaults.get('webp', {}).get('method', 6))
        tk.Spinbox(compression_frame, from_=0, to=6, textvariable=self.compression_vars['webp_method'], width=10).grid(row=comp_row, column=1, sticky="w", padx=(8, 0))
        comp_row += 1

        tk.Label(compression_frame, text="Alpha quality (0-100):").grid(row=comp_row, column=0, sticky="w")
        self.compression_vars['webp_alpha_quality'] = tk.IntVar(value=compression_defaults.get('webp', {}).get('alpha_quality', 100))
        tk.Spinbox(compression_frame, from_=0, to=100, textvariable=self.compression_vars['webp_alpha_quality'], width=10).grid(row=comp_row, column=1, sticky="w", padx=(8, 0))
        comp_row += 1

        self.compression_vars['webp_exact'] = tk.BooleanVar(value=compression_defaults.get('webp', {}).get('exact', True))
        tk.Checkbutton(compression_frame, text="Exact WebP", variable=self.compression_vars['webp_exact']).grid(row=comp_row, column=0, columnspan=2, sticky="w")
        comp_row += 1

        tk.Label(compression_frame, text="AVIF Settings", font=("Arial", 9, "bold")).grid(row=comp_row, column=0, columnspan=3, sticky="w", pady=(12, 2))
        comp_row += 1

        self.compression_vars['avif_lossless'] = tk.BooleanVar(value=compression_defaults.get('avif', {}).get('lossless', True))
        tk.Checkbutton(compression_frame, text="Lossless AVIF", variable=self.compression_vars['avif_lossless']).grid(row=comp_row, column=0, columnspan=2, sticky="w")
        comp_row += 1

        tk.Label(compression_frame, text="Quality (0-100):").grid(row=comp_row, column=0, sticky="w")
        self.compression_vars['avif_quality'] = tk.IntVar(value=compression_defaults.get('avif', {}).get('quality', 100))
        tk.Spinbox(compression_frame, from_=0, to=100, textvariable=self.compression_vars['avif_quality'], width=10).grid(row=comp_row, column=1, sticky="w", padx=(8, 0))
        comp_row += 1

        tk.Label(compression_frame, text="Speed (0-10):").grid(row=comp_row, column=0, sticky="w")
        self.compression_vars['avif_speed'] = tk.IntVar(value=compression_defaults.get('avif', {}).get('speed', 5))
        tk.Spinbox(compression_frame, from_=0, to=10, textvariable=self.compression_vars['avif_speed'], width=10).grid(row=comp_row, column=1, sticky="w", padx=(8, 0))
        comp_row += 1

        tk.Label(compression_frame, text="TIFF Settings", font=("Arial", 9, "bold")).grid(row=comp_row, column=0, columnspan=3, sticky="w", pady=(12, 2))
        comp_row += 1

        tk.Label(compression_frame, text="Compression type:").grid(row=comp_row, column=0, sticky="w")
        self.compression_vars['tiff_compression_type'] = tk.StringVar(value=compression_defaults.get('tiff', {}).get('compression_type', 'lzw'))
        tk.OptionMenu(compression_frame, self.compression_vars['tiff_compression_type'], 'lzw', 'jpeg', 'tiff_adobe_deflate', 'tiff_deflate', 'raw').grid(row=comp_row, column=1, sticky="w", padx=(8, 0))
        comp_row += 1

        tk.Label(compression_frame, text="Quality (0-100):").grid(row=comp_row, column=0, sticky="w")
        self.compression_vars['tiff_quality'] = tk.IntVar(value=compression_defaults.get('tiff', {}).get('quality', 100))
        tk.Spinbox(compression_frame, from_=0, to=100, textvariable=self.compression_vars['tiff_quality'], width=10).grid(row=comp_row, column=1, sticky="w", padx=(8, 0))
        comp_row += 1

        self.compression_vars['tiff_optimize'] = tk.BooleanVar(value=compression_defaults.get('tiff', {}).get('optimize', True))
        tk.Checkbutton(compression_frame, text="Optimize TIFF", variable=self.compression_vars['tiff_optimize']).grid(row=comp_row, column=0, columnspan=2, sticky="w")
        comp_row += 1

        compression_frame.update_idletasks()
        req_width = compression_frame.winfo_reqwidth() + 3
        req_height = compression_frame.winfo_reqheight() + 3
        compression_canvas.configure(width=req_width, height=min(req_height, 200))
        compression_canvas.update_idletasks()
        compression_canvas.yview_moveto(0)
        compression_canvas.xview_moveto(0)

    def reset_to_defaults(self):
        cpu_default = str((self.max_threads + 1) // 4)
        self.cpu_var.set(cpu_default)
        default_mem = ((self.max_memory_mb // 4 + 9) // 10) * 10
        self.mem_var.set(str(default_mem))

        defaults = self.app_config.DEFAULTS["extraction_defaults"]

        for key, (var_type, _) in self.extraction_fields.items():
            default_val = defaults.get(key, "" if var_type is tk.StringVar else False)
            if var_type is tk.BooleanVar:
                self.extraction_vars[key].set(default_val)
            else:
                self.extraction_vars[key].set(str(default_val))

        update_defaults = self.app_config.DEFAULTS["update_settings"]
        self.check_updates_var.set(update_defaults.get("check_updates_on_startup", True))
        self.auto_update_var.set(update_defaults.get("auto_download_updates", False))

        compression_defaults = self.app_config.DEFAULTS["compression_defaults"]

        self.compression_vars['png_compress_level'].set(compression_defaults.get('png', {}).get('compress_level', 9))
        self.compression_vars['png_optimize'].set(compression_defaults.get('png', {}).get('optimize', True))

        self.compression_vars['webp_lossless'].set(compression_defaults.get('webp', {}).get('lossless', True))
        self.compression_vars['webp_quality'].set(compression_defaults.get('webp', {}).get('quality', 100))
        self.compression_vars['webp_method'].set(compression_defaults.get('webp', {}).get('method', 6))
        self.compression_vars['webp_alpha_quality'].set(compression_defaults.get('webp', {}).get('alpha_quality', 100))
        self.compression_vars['webp_exact'].set(compression_defaults.get('webp', {}).get('exact', True))

        self.compression_vars['avif_lossless'].set(compression_defaults.get('avif', {}).get('lossless', True))
        self.compression_vars['avif_quality'].set(compression_defaults.get('avif', {}).get('quality', 100))
        self.compression_vars['avif_speed'].set(compression_defaults.get('avif', {}).get('speed', 0))

        self.compression_vars['tiff_compression_type'].set(compression_defaults.get('tiff', {}).get('compression_type', 'lzw'))
        self.compression_vars['tiff_quality'].set(compression_defaults.get('tiff', {}).get('quality', 90))
        self.compression_vars['tiff_optimize'].set(compression_defaults.get('tiff', {}).get('optimize', True))

        print("[Config] Configuration has been reset to defaults.")

    def save_config(self):
        cpu_val = self.cpu_var.get().strip().lower()
        if cpu_val != 'auto':
            try:
                if not cpu_val.isdigit():
                    tk.messagebox.showerror(
                        "Invalid Input",
                        "CPU cores must be a positive integer or 'auto'."
                    )
                    return
                cpu_int = int(cpu_val)
                if cpu_int < 1:
                    tk.messagebox.showerror(
                        "Invalid Input",
                        "CPU cores must be at least 1."
                    )
                    return
                if cpu_int > self.max_cores:
                    tk.messagebox.showerror(
                        "Invalid Input",
                        f"CPU cores cannot exceed {self.max_cores}."
                    )
                    return
            except Exception as e:
                tk.messagebox.showerror(
                    "Unexpected error",
                    f"An unexpected error occurred while validating CPU cores input.\n"
                    "This is most likely a bug in in the app and not a user error.\n"
                    "Please report this issue on GitHub with the error details and your input.\n\n"
                    f"Input: '{cpu_val}'\nError: {str(e)}"
                )
                return

        resource_limits = self.app_config.get("resource_limits", {})
        resource_limits["cpu_cores"] = cpu_val

        mem_val = self.mem_var.get().strip()
        try:
            mem_int = int(mem_val)
            if mem_int < 0:
                raise ValueError
            if mem_int > self.max_memory_mb:
                tk.messagebox.showerror(
                    "Invalid Input",
                    f"Memory limit cannot exceed {self.max_memory_mb} MB."
                )
                return
            resource_limits["memory_limit_mb"] = mem_int
        except Exception:
            tk.messagebox.showerror(
                "Invalid Input",
                "Memory limit must be a non-negative integer."
            )
            return

        self.app_config.set("resource_limits", resource_limits)
        self.app_config.save()

        extraction_defaults = {}
        for key, (var_type, _) in self.extraction_fields.items():
            val = self.extraction_vars[key].get()
            expected_type = self.app_config.TYPE_MAP[key]
            try:
                extraction_defaults[key] = self.parse_value(key, val, expected_type)
            except ValueError as e:
                tk.messagebox.showerror("Invalid Input", f"Invalid value for '{key}': '{val}'\n{str(e)}")
                return
            except Exception as err:
                tk.messagebox.showerror("Invalid Input", str(err))
                return
        self.app_config.set_extraction_defaults(**extraction_defaults)

        update_settings = {
            "check_updates_on_startup": self.check_updates_var.get(),
            "auto_download_updates": self.auto_update_var.get() if self.check_updates_var.get() else False,
        }
        self.app_config.set("update_settings", update_settings)

        self.app_config.set_compression_defaults('png',
            compress_level=self.compression_vars['png_compress_level'].get(),
            optimize=self.compression_vars['png_optimize'].get()
        )

        self.app_config.set_compression_defaults('webp',
            lossless=self.compression_vars['webp_lossless'].get(),
            quality=self.compression_vars['webp_quality'].get(),
            method=self.compression_vars['webp_method'].get(),
            alpha_quality=self.compression_vars['webp_alpha_quality'].get(),
            exact=self.compression_vars['webp_exact'].get()
        )

        self.app_config.set_compression_defaults('avif',
            lossless=self.compression_vars['avif_lossless'].get(),
            quality=self.compression_vars['avif_quality'].get(),
            speed=self.compression_vars['avif_speed'].get()
        )

        self.app_config.set_compression_defaults('tiff',
            compression_type=self.compression_vars['tiff_compression_type'].get(),
            quality=self.compression_vars['tiff_quality'].get(),
            optimize=self.compression_vars['tiff_optimize'].get()
        )

        self.app_config.save()
        self.window.destroy()

    @staticmethod
    def parse_value(key, val, expected_type):
        if expected_type is bool:
            if isinstance(val, str):
                if val.lower() in ("1", "true", "yes", "on"):
                    return True
                elif val.lower() in ("0", "false", "no", "off"):
                    return False
                else:
                    raise ValueError(ExceptionHandler.handle_validation_error(key, expected_type))
            return bool(val)
        try:
            return expected_type(val)
        except Exception:
            raise ValueError(ExceptionHandler.handle_validation_error(key, expected_type))
