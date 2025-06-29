import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading


class DebugWindow:
    """
    A debug window for displaying real-time process information.

    This window provides a console-like interface for displaying debug messages
    and process status information to the user. It runs independently of other
    toplevel windows and can be toggled on/off based on user preferences.

    Attributes:
        window (tk.Toplevel): The debug window instance.
        console_frame (tk.Frame): Frame containing the console text and scrollbar.
        console_text (tk.Text): Text widget for logging debug messages.
        scrollbar (ttk.Scrollbar): Scrollbar for the console text widget.
        is_closed (bool): Flag to track if the window has been closed.
        _lock (threading.Lock): Thread lock for safe text updates.

    Methods:
        __init__(parent, title="Debug Console", width=600, height=400):
            Initialize the debug window with console display.
        log(message, level="info"):
            Log a message to the debug console with timestamp and level.
        clear():
            Clear all messages from the debug console.
        close():
            Close the debug window and mark it as closed.
        is_window_closed():
            Check if the window has been closed.
    """

    def __init__(self, parent, title="Debug Console", width=600, height=400):
        """
        Initialize the debug window.
        
        Args:
            parent: Parent tkinter window
            title: Window title
            width: Window width in pixels
            height: Window height in pixels
        """
        self.is_closed = False
        self._lock = threading.Lock()
        
        try:
            # Create debug window as a completely independent window
            # Using a new Tk instance instead of Toplevel to avoid interference with grab_set() from modal dialogs
            self.window = tk.Tk()
            self.window.title(title)
            self.window.geometry(f"{width}x{height}")
            self.window.configure(bg='#1e1e1e')
            
            # Make the window stay on top of modal dialogs but not always on top of everything
            # This ensures it remains visible even when modal dialogs are open
            self.window.attributes('-topmost', True)
            # Lower topmost after a brief moment to avoid being annoying
            self.window.after(100, lambda: self.window.attributes('-topmost', False) if self.window else None)
            
            # Position the window in a convenient location (top-right corner of screen)
            screen_width = self.window.winfo_screenwidth()
            x_position = screen_width - width - 50  # 50px from right edge
            y_position = 50  # 50px from top
            self.window.geometry(f"{width}x{height}+{x_position}+{y_position}")
            
            # Ensure window stays focused and visible
            self.window.focus_force()
            self.window.lift()
            
            # Set up console frame
            self.console_frame = tk.Frame(self.window, bg='#1e1e1e')
            self.console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Create console text widget
            self.console_text = tk.Text(
                self.console_frame,
                bg='#1e1e1e',
                fg='#ffffff',
                font=('Consolas', 10),
                insertbackground='#ffffff',
                selectbackground='#3d3d3d',
                wrap=tk.WORD,
                state=tk.DISABLED
            )
            
            # Create scrollbar
            self.scrollbar = ttk.Scrollbar(
                self.console_frame, 
                orient=tk.VERTICAL, 
                command=self.console_text.yview
            )
            self.console_text.configure(yscrollcommand=self.scrollbar.set)
            
            # Pack console and scrollbar
            self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Create button frame
            button_frame = tk.Frame(self.window, bg='#1e1e1e')
            button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            # Clear button
            clear_btn = tk.Button(
                button_frame,
                text="Clear",
                command=self.clear,
                bg='#444444',
                fg='white',
                font=('Arial', 9),
                relief=tk.FLAT,
                padx=20
            )
            clear_btn.pack(side=tk.LEFT)
            
            # Close button
            close_btn = tk.Button(
                button_frame,
                text="Close",
                command=self.close,
                bg='#444444',
                fg='white',
                font=('Arial', 9),
                relief=tk.FLAT,
                padx=20
            )
            close_btn.pack(side=tk.RIGHT)
            
            # Configure text tags for different log levels
            self.console_text.tag_configure("info", foreground="#00ff00")
            self.console_text.tag_configure("warning", foreground="#ffff00")
            self.console_text.tag_configure("error", foreground="#ff0000")
            self.console_text.tag_configure("success", foreground="#00ff88")
            self.console_text.tag_configure("timestamp", foreground="#888888")
            
            # Handle window close event
            self.window.protocol("WM_DELETE_WINDOW", self.close)
            
            # Log initial message
            self.log("Debug console initialized", "info")
            
        except Exception as e:
            print(f"Error creating debug window: {e}")
            self.is_closed = True
            self.window = None

    def log(self, message, level="info"):
        """
        Log a message to the debug console.
        
        Args:
            message: The message to log
            level: Log level (info, warning, error, success)
        """
        if self.is_closed or not hasattr(self, 'window') or not self.window:
            return
            
        try:
            with self._lock:
                self.window.after(0, self._log_safe, message, level)
        except Exception:
            # Window might be closed, ignore errors
            pass

    def _log_safe(self, message, level):
        """Thread-safe logging method."""
        try:
            if self.is_closed or not self.window:
                return
                
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            self.console_text.config(state=tk.NORMAL)
            self.console_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.console_text.insert(tk.END, f"{message}\n", level)
            self.console_text.see(tk.END)
            self.console_text.config(state=tk.DISABLED)
            
            self.window.update_idletasks()
        except Exception:
            # Window might be closed, ignore errors
            pass

    def clear(self):
        """Clear all messages from the debug console."""
        if self.is_closed or not hasattr(self, 'window') or not self.window:
            return
            
        try:
            with self._lock:
                self.window.after(0, self._clear_safe)
        except Exception:
            pass

    def _clear_safe(self):
        """Thread-safe clear method."""
        try:
            if self.is_closed or not self.window:
                return
                
            self.console_text.config(state=tk.NORMAL)
            self.console_text.delete(1.0, tk.END)
            self.console_text.config(state=tk.DISABLED)
            self.log("Debug console cleared", "info")
        except Exception:
            pass

    def close(self):
        """Close the debug window."""
        try:
            self.is_closed = True
            if hasattr(self, 'window') and self.window:
                self.window.destroy()
                self.window = None
        except Exception:
            pass

    def bring_to_front(self):
        """Bring the debug window to the front, useful when modal dialogs are opened."""
        if self.is_closed or not hasattr(self, 'window') or not self.window:
            return
            
        try:
            # Temporarily set topmost to bring window to front
            self.window.attributes('-topmost', True)
            self.window.focus_force()
            self.window.lift()
            # Remove topmost after a moment
            self.window.after(100, lambda: self.window.attributes('-topmost', False) if self.window else None)
        except Exception:
            pass

    def is_window_closed(self):
        """Check if the window has been closed."""
        return self.is_closed or not hasattr(self, 'window') or not self.window


# Global debug window instance
_debug_window = None
_debug_window_lock = threading.Lock()


def print_to_ui(message, level="info"):
    """
    Print a message to the debug UI window if it exists and is open.
    
    This function provides a simple interface similar to print() but outputs
    to the debug window instead of (or in addition to) the console.
    
    Args:
        message: The message to display
        level: Log level (info, warning, error, success)
    """
    global _debug_window
    
    # Always print to console as well
    print(message)
    
    # If debug window exists and is not closed, also log there
    with _debug_window_lock:
        if _debug_window and not _debug_window.is_window_closed():
            _debug_window.log(str(message), level)


def create_debug_window(parent, title="Debug Console"):
    """
    Create a new debug window.
    
    Args:
        parent: Parent tkinter window
        title: Window title
        
    Returns:
        DebugWindow instance or None if creation failed
    """
    global _debug_window
    
    with _debug_window_lock:
        # Close existing window if it exists
        if _debug_window and not _debug_window.is_window_closed():
            _debug_window.close()
        
        # Create new window
        try:
            _debug_window = DebugWindow(parent, title)
            return _debug_window
        except Exception as e:
            print(f"Failed to create debug window: {e}")
            _debug_window = None
            return None


def close_debug_window():
    """Close the debug window if it exists."""
    global _debug_window
    
    with _debug_window_lock:
        if _debug_window:
            _debug_window.close()
            _debug_window = None


def bring_debug_window_to_front():
    """Bring the debug window to the front if it exists."""
    global _debug_window
    
    with _debug_window_lock:
        if _debug_window and not _debug_window.is_window_closed():
            _debug_window.bring_to_front()


def is_debug_window_open():
    """Check if the debug window is currently open."""
    global _debug_window
    
    with _debug_window_lock:
        return _debug_window and not _debug_window.is_window_closed()
