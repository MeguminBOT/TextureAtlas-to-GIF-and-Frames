import tkinter as tk
from tkinter import messagebox
import psutil
import multiprocessing
import platform
import subprocess

from core.exception_handler import ExceptionHandler

class AppConfigWindow:
    """
    A window for configuring application resource usage and displaying system information.

    Attributes:
        window (tk.Toplevel): The options window instance.
        app_config: The application's configuration object (AppConfig).
        max_cores (int): Number of logical CPU cores available.
        max_threads (int): Number of logical CPU threads available (may be same as max_cores).
        max_memory_mb (int): Total physical RAM in megabytes.
        cpu_var (tk.StringVar): Tkinter variable for CPU threads input field.
        mem_var (tk.StringVar): Tkinter variable for memory limit input field.
        default_animation_format_var (tk.StringVar): Tkinter variable for default animation format.
        default_fps_var (tk.StringVar): Tkinter variable for default frames per second.
        default_delay_var (tk.StringVar): Tkinter variable for default loop delay in milliseconds.
        default_period_var (tk.StringVar): Tkinter variable for default minimum period in milliseconds.
        default_scale_var (tk.StringVar): Tkinter variable for default scale factor.
        default_threshold_var (tk.StringVar): Tkinter variable for default alpha threshold.
        default_crop_var (tk.StringVar): Tkinter variable for default cropping method.
        default_keepframes_var (tk.StringVar): Tkinter variable for default keep frames option.
        default_filename_format_var (tk.StringVar): Tkinter variable for default filename format.
        default_variable_delay_var (tk.BooleanVar): Tkinter variable for variable delay option.
        default_fnf_idle_loop_var (tk.BooleanVar): Tkinter variable for FNF idle loop option.

    Methods:
        __init__(parent, app_config):
            Initialize the options window with system information and current settings.
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
    """

    def __init__(self, parent, app_config):
        self.window = tk.Toplevel(parent)
        self.window.title("App options")
        self.window.geometry("460x580")
        self.app_config = app_config

        # Get system limits
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


        main_frame = tk.Frame(self.window)
        main_frame.pack(anchor="w", padx=12, pady=8, fill="both", expand=True)

        row = 0
        tk.Label(main_frame, text="Your computer", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(0, 2), columnspan=2)
        row += 1
        tk.Label(main_frame, text=f"CPU: {cpu_model} (Threads: {self.max_threads})", font=("Arial", 9)).grid(row=row, column=0, sticky="w", columnspan=2)
        row += 1
        tk.Label(main_frame, text=f"RAM: {self.max_memory_mb:,} MB", font=("Arial", 9)).grid(row=row, column=0, sticky="w", pady=(0, 8), columnspan=2)
        row += 1

        tk.Label(main_frame, text="App resource limits", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(0, 4), columnspan=2)
        row += 1
        resource_canvas = tk.Canvas(main_frame, borderwidth=1, relief="solid", highlightthickness=1, highlightbackground="#888")
        resource_canvas.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8), padx=(0, 0))
        resource_frame = tk.Frame(resource_canvas, padx=4, pady=4)

        tk.Label(resource_frame, text=f"CPU threads to use (max: {self.max_threads}):").grid(row=0, column=0, sticky="w")
        resource_limits = self.app_config.get("resource_limits", {})
        default_threads = (self.max_threads + 1) // 4
        
        cpu_default = resource_limits.get("cpu_cores", "auto")
        if cpu_default is None or cpu_default == "auto":
            cpu_default = str(default_threads)
        
        self.cpu_var = tk.StringVar(value=str(cpu_default))
        self.cpu_entry = tk.Entry(resource_frame, textvariable=self.cpu_var, width=10)
        self.cpu_entry.grid(row=0, column=1, sticky="w", padx=(8,0))

        # Memory limit is not actually implemented in the app yet as it requires vast code changes but we add it for future use
        tk.Label(resource_frame, text=f"Memory limit (MB, max: {self.max_memory_mb}):").grid(row=1, column=0, sticky="w", pady=(4,0))
        default_mem = ((self.max_memory_mb // 4 + 9) // 10) * 10
        mem_default = resource_limits.get("memory_limit_mb", 0)
        
        if mem_default is None or mem_default == 0:
            mem_default = str(default_mem)
        
        self.mem_var = tk.StringVar(value=str(mem_default))
        self.mem_entry = tk.Entry(resource_frame, textvariable=self.mem_var, width=10, state="disabled")
        self.mem_entry.grid(row=1, column=1, sticky="w", padx=(8,0))

        resource_frame.update_idletasks()
        req_width = resource_frame.winfo_reqwidth() + 3
        req_height = resource_frame.winfo_reqheight() + 3
        resource_canvas.configure(width=req_width, height=req_height)
        resource_canvas.update_idletasks()
        resource_canvas.yview_moveto(0)
        resource_canvas.xview_moveto(0)
        resource_canvas.create_window((0, 0), window=resource_frame, anchor="nw")
        
        row += 1        
        tk.Label(main_frame, text="Extraction defaults", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(16, 2), columnspan=2)
        row += 1
        defaults = self.app_config.get_extraction_defaults() if hasattr(self.app_config, 'get_extraction_defaults') else {}

        resource_frame.update_idletasks()

        extraction_outer_frame = tk.Frame(main_frame, borderwidth=1, relief="solid", highlightthickness=1, highlightbackground="#888")
        extraction_outer_frame.grid(row=row, column=0, columnspan=2, sticky="nsew", padx=(0, 0), pady=(0, 10))

        extraction_canvas = tk.Canvas(extraction_outer_frame, borderwidth=0, highlightthickness=0)
        extraction_canvas.pack(side="left", fill="both", expand=True)

        extraction_scrollbar = tk.Scrollbar(extraction_outer_frame, orient="vertical", command=extraction_canvas.yview)
        extraction_scrollbar.pack(side="right", fill="y")
        extraction_canvas.configure(yscrollcommand=extraction_scrollbar.set)

        extraction_frame = tk.Frame(extraction_canvas, padx=4, pady=4)
        canvas_window = extraction_canvas.create_window((0, 0), window=extraction_frame, anchor="nw")

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

        # Doesn't work fully but better than nothing for now.
        if platform.system() == "Windows" or platform.system() == "Darwin":
            extraction_canvas.bind("<MouseWheel>", _on_mousewheel)
        elif platform.system() == "Linux":
            extraction_canvas.bind("<Button-4>", _on_linux_scroll)
            extraction_canvas.bind("<Button-5>", _on_linux_scroll)

        option_row = 0
        tk.Label(extraction_frame, text="Animation Format:").grid(row=option_row, column=0, sticky="w")
        self.default_animation_format_var = tk.StringVar(value=defaults.get("animation_format", "None"))
        self.default_animation_format_menu = tk.OptionMenu(extraction_frame, self.default_animation_format_var, "None", "GIF", "WebP", "APNG")
        self.default_animation_format_menu.grid(row=option_row, column=1, sticky="w", padx=(8,0))
        option_row += 1

        tk.Label(extraction_frame, text="Frame rate (fps):").grid(row=option_row, column=0, sticky="w")
        self.default_fps_var = tk.StringVar(value=str(defaults.get("fps", 24)))
        self.default_fps_entry = tk.Entry(extraction_frame, textvariable=self.default_fps_var, width=10)
        self.default_fps_entry.grid(row=option_row, column=1, sticky="w", padx=(8,0))
        option_row += 1

        tk.Label(extraction_frame, text="Loop delay (ms):").grid(row=option_row, column=0, sticky="w")
        self.default_delay_var = tk.StringVar(value=str(defaults.get("delay", 250)))
        self.default_delay_entry = tk.Entry(extraction_frame, textvariable=self.default_delay_var, width=10)
        self.default_delay_entry.grid(row=option_row, column=1, sticky="w", padx=(8,0))
        option_row += 1

        tk.Label(extraction_frame, text="Min period (ms):").grid(row=option_row, column=0, sticky="w")
        self.default_period_var = tk.StringVar(value=str(defaults.get("period", 0)))
        self.default_period_entry = tk.Entry(extraction_frame, textvariable=self.default_period_var, width=10)
        self.default_period_entry.grid(row=option_row, column=1, sticky="w", padx=(8,0))
        option_row += 1

        tk.Label(extraction_frame, text="Scale:").grid(row=option_row, column=0, sticky="w")
        self.default_scale_var = tk.StringVar(value=str(defaults.get("scale", 1.0)))
        self.default_scale_entry = tk.Entry(extraction_frame, textvariable=self.default_scale_var, width=10)
        self.default_scale_entry.grid(row=option_row, column=1, sticky="w", padx=(8,0))
        option_row += 1

        tk.Label(extraction_frame, text="Alpha threshold:").grid(row=option_row, column=0, sticky="w")
        self.default_threshold_var = tk.StringVar(value=str(defaults.get("threshold", 0.5)))
        self.default_threshold_entry = tk.Entry(extraction_frame, textvariable=self.default_threshold_var, width=10)
        self.default_threshold_entry.grid(row=option_row, column=1, sticky="w", padx=(8,0))
        option_row += 1

        tk.Label(extraction_frame, text="Cropping method:").grid(row=option_row, column=0, sticky="w")
        self.default_crop_var = tk.StringVar(value=defaults.get("crop_option", "Animation based"))
        self.default_crop_menu = tk.OptionMenu(extraction_frame, self.default_crop_var, "None", "Animation based", "Frame based")
        self.default_crop_menu.grid(row=option_row, column=1, sticky="w", padx=(8,0))
        option_row += 1

        tk.Label(extraction_frame, text="Keep frames:").grid(row=option_row, column=0, sticky="w")
        self.default_keepframes_var = tk.StringVar(value=defaults.get("keep_frames", "All"))
        self.default_keepframes_menu = tk.OptionMenu(extraction_frame, self.default_keepframes_var, "None", "All", "No duplicates", "First", "Last", "First, Last")
        self.default_keepframes_menu.grid(row=option_row, column=1, sticky="w", padx=(8,0))
        option_row += 1

        tk.Label(extraction_frame, text="Filename format:").grid(row=option_row, column=0, sticky="w")
        self.default_filename_format_var = tk.StringVar(value=defaults.get("filename_format", "Standardized"))
        self.default_filename_format_menu = tk.OptionMenu(extraction_frame, self.default_filename_format_var, "Standardized", "No spaces", "No special characters")
        self.default_filename_format_menu.grid(row=option_row, column=1, sticky="w", padx=(8,0))
        option_row += 1

        tk.Label(extraction_frame, text="Variable delay:").grid(row=option_row, column=0, sticky="w")
        self.default_variable_delay_var = tk.BooleanVar(value=defaults.get("variable_delay", False))
        self.default_variable_delay_check = tk.Checkbutton(extraction_frame, variable=self.default_variable_delay_var)
        self.default_variable_delay_check.grid(row=option_row, column=1, sticky="w", padx=(8,0))
        option_row += 1

        tk.Label(extraction_frame, text="FNF idle loop (sets loop delay to 0):").grid(row=option_row, column=0, sticky="w")
        self.default_fnf_idle_loop_var = tk.BooleanVar(value=defaults.get("fnf_idle_loop", False))
        self.default_fnf_idle_loop_check = tk.Checkbutton(extraction_frame, variable=self.default_fnf_idle_loop_var)
        self.default_fnf_idle_loop_check.grid(row=option_row, column=1, sticky="w", padx=(8,0))
        option_row += 1

        button_frame = tk.Frame(self.window)
        button_frame.pack(side="bottom", pady=10)
        tk.Button(button_frame, text="Save", command=self.save_config, width=12).pack(side="left", padx=10)
        tk.Button(button_frame, text="Cancel", command=self.window.destroy, width=12).pack(side="left", padx=10)
        tk.Button(button_frame, text="Reset to defaults", command=self.reset_to_defaults, width=18).pack(side="left", padx=10)

    def reset_to_defaults(self):
        """Reset all fields to the application's initial defaults."""
        cpu_default = str((self.max_threads + 1) // 4)
        self.cpu_var.set(cpu_default)
        default_mem = ((self.max_memory_mb // 4 + 9) // 10) * 10
        self.mem_var.set(str(default_mem))

        defaults = self.app_config.DEFAULTS["extraction_defaults"]
        self.default_animation_format_var.set(defaults.get("animation_format", "None"))
        self.default_fps_var.set(str(defaults.get("fps", 24)))
        self.default_delay_var.set(str(defaults.get("delay", 250)))
        self.default_period_var.set(str(defaults.get("period", 0)))
        self.default_scale_var.set(str(defaults.get("scale", 1.0)))
        self.default_threshold_var.set(str(defaults.get("threshold", 0.5)))
        self.default_crop_var.set(defaults.get("crop_option", "Animation based"))
        self.default_keepframes_var.set(defaults.get("keep_frames", "All"))
        self.default_filename_format_var.set(defaults.get("filename_format", "Standardized"))
        self.default_variable_delay_var.set(defaults.get("variable_delay", False))
        self.default_fnf_idle_loop_var.set(defaults.get("fnf_idle_loop", False))
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

        # Not correctly implemented yet.
        raw_values = {
            "animation_format": self.default_animation_format_var.get(),
            "fps": self.default_fps_var.get(),
            "delay": self.default_delay_var.get(),
            "period": self.default_period_var.get(),
            "scale": self.default_scale_var.get(),
            "threshold": self.default_threshold_var.get(),
            "crop_option": self.default_crop_var.get(),
            "keep_frames": self.default_keepframes_var.get(),
            "filename_format": self.default_filename_format_var.get(),
            "variable_delay": self.default_variable_delay_var.get(),
            "fnf_idle_loop": self.default_fnf_idle_loop_var.get(),
        }

        extraction_defaults = {}

        type_error_occurred = False
        for key, val in raw_values.items():
            try:
                extraction_defaults[key] = self.app_config.TYPE_MAP[key](val)
            except (TypeError, ValueError) as e:
                msg = ExceptionHandler.handle_validation_error(key, self.app_config.TYPE_MAP[key])
                if not msg:
                    msg = f"Invalid value for '{key}': {val}\n\nError: {str(e)}"
                messagebox.showerror("Invalid Input", f"{msg}\n\nError: {str(e)}")
                type_error_occurred = True
                break
            except Exception as err:
                messagebox.showerror("Invalid Input", str(err))
                return

        if type_error_occurred:
            return

        self.app_config.set_extraction_defaults(**extraction_defaults)
        self.window.destroy()
