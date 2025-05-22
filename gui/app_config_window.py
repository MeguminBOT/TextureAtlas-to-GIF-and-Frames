import tkinter as tk
import psutil
import multiprocessing
import platform
import subprocess

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
        cpu_entry (tk.Entry): Entry widget for CPU threads.
        mem_var (tk.StringVar): Tkinter variable for memory limit input field.
        mem_entry (tk.Entry): Entry widget for memory limit.

    Methods:
        save_config():
            Validate and save user settings to the app config.
    """

    def __init__(self, parent, app_config):
        self.window = tk.Toplevel(parent)
        self.window.title("App Options")
        self.window.geometry("480x360")
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


        tk.Label(self.window, text="Your computer", font=("Arial", 10, "bold")).pack(pady=(10, 2))
        tk.Label(self.window, text=f"{cpu_model}  (Threads: {self.max_threads})", font=("Arial", 9)).pack()
        tk.Label(self.window, text=f"RAM: {self.max_memory_mb:,} MB", font=("Arial", 9)).pack(pady=(0, 8))

        tk.Label(self.window, text="App resource limits", font=("Arial", 10, "bold")).pack(pady=(8, 2))
        tk.Label(self.window, text=f"CPU Threads to Use (max: {self.max_threads}):").pack()
        default_threads = (self.max_threads + 1) // 2
        cpu_default = self.app_config.get("cpu_cores")
        if cpu_default is None or cpu_default == "auto":
            cpu_default = str(default_threads)
        self.cpu_var = tk.StringVar(value=str(cpu_default))
        self.cpu_entry = tk.Entry(self.window, textvariable=self.cpu_var)
        self.cpu_entry.pack()

        tk.Label(self.window, text=f"Memory Limit (MB, max: {self.max_memory_mb}):").pack(pady=(12, 0))
        default_mem = ((self.max_memory_mb // 2 + 9) // 10) * 10
        mem_default = self.app_config.get("memory_limit_mb")
        if mem_default is None or mem_default == 0:
            mem_default = str(default_mem)
        self.mem_var = tk.StringVar(value=str(mem_default))
        self.mem_entry = tk.Entry(self.window, textvariable=self.mem_var)
        self.mem_entry.pack()

        tk.Button(
            self.window, text="Save", command=self.save_config
        ).pack(pady=12)

    def save_config(self):
        cpu_val = self.cpu_var.get().strip().lower()
        if cpu_val != 'auto':
            try:
                cpu_int = int(cpu_val)
                if cpu_int < 1:
                    raise ValueError

                if cpu_int > self.max_cores:
                    tk.messagebox.showerror(
                        "Invalid Input",
                        f"CPU cores cannot exceed {self.max_cores}."
                    )
                    return
            except Exception:
                tk.messagebox.showerror(
                    "Invalid Input",
                    "CPU cores must be a positive integer or 'auto'."
                )
                return
        self.app_config.set("cpu_cores", cpu_val)
        self.app_config.save()

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

            self.app_config.set("memory_limit_mb", mem_int)
            self.app_config.save()
        except Exception:
            tk.messagebox.showerror(
                "Invalid Input",
                "Memory limit must be a non-negative integer."
            )
            return
        self.window.destroy()
