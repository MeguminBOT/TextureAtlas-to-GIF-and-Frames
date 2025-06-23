import tkinter as tk


class Tooltip:
    """
    Creates a tooltip popup window for a tk.Widget when hovering over it.

    The tooltip appears after a delay and disappears when the mouse leaves the widget.
    """

    def __init__(self, widget, text, delay=250):
        """
        Initialize the tooltip.

        Args:
            widget: The widget to attach the tooltip to
            text: The text to display in the tooltip
            delay: Delay in milliseconds before showing the tooltip (default: 250)
        """

        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.after_id = None

        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Motion>", self.on_motion)

    def on_enter(self, event=None):
        """Handle mouse entering the widget."""
        self.schedule_tooltip()

    def on_leave(self, event=None):
        """Handle mouse leaving the widget."""
        self.cancel_tooltip()
        self.hide_tooltip()

    def on_motion(self, event=None):
        """Handle mouse motion within the widget."""
        self.cancel_tooltip()
        self.schedule_tooltip()

    def schedule_tooltip(self):
        """Schedule the tooltip to appear after the delay."""
        self.cancel_tooltip()
        self.after_id = self.widget.after(self.delay, self.show_tooltip)

    def cancel_tooltip(self):
        """Cancel any scheduled tooltip."""
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def show_tooltip(self):
        """Show the tooltip popup."""
        if self.tooltip_window or not self.text:
            return

        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("Arial", 9),
            wraplength=300,
        )
        label.pack(ipadx=1)

    def hide_tooltip(self):
        """Hide the tooltip popup."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
