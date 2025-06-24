import tkinter as tk
from tkinter import ttk


class BackgroundColorDetectionWindow:
    """
    A GUI window that displays detected background colors for unknown spritesheets and provides 
    options for handling them.

    This window shows a list of unknown spritesheets with their detected background colors,
    displays color samples, and allows the user to choose how to handle background removal.
    """

    @staticmethod
    def show_detection_results(parent_window, detection_results):
        """
        Show the background color detection results dialog.

        Args:
            parent_window: The parent tkinter window
            detection_results: List of dictionaries with keys:
                - 'filename': Name of the spritesheet file
                - 'colors': List of RGB tuples for detected background colors
                - 'has_transparency': Boolean indicating if image already has transparency

        Returns:
            str: User's choice - 'key_background', 'exclude_background', or 'cancel'
        """
        
        if not detection_results:
            return 'cancel'

        dialog = tk.Toplevel(parent_window)
        dialog.title("Background Colors Detected")
        dialog.geometry("700x500")
        dialog.resizable(True, True)
        dialog.transient(parent_window)
        dialog.grab_set()

        # Center the dialog relative to parent window
        dialog.geometry("+%d+%d" % (
            parent_window.winfo_rootx() + 50,
            parent_window.winfo_rooty() + 50
        ))

        result = {'action': 'cancel'}

        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        # Title frame with icon
        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 15))

        warning_label = tk.Label(title_frame, text="🎨", font=("Arial", 24))
        warning_label.pack(side="left")
        title_label = tk.Label(title_frame, text="Background Colors Detected", 
                              font=("Arial", 14, "bold"))
        title_label.pack(side="left", padx=(10, 0))

        # Description
        description = (
            f"Detected background colors in {len(detection_results)} unknown spritesheet(s).\n"
            f"Choose how to handle these background colors during sprite extraction:"
        )
        
        desc_label = tk.Label(main_frame, text=description, font=("Arial", 10), 
                             justify="left", wraplength=650)
        desc_label.pack(fill="x", pady=(0, 10))

        # Scrollable frame for the detection results
        canvas_frame = tk.Frame(main_frame)
        canvas_frame.pack(fill="both", expand=True, pady=(0, 15))

        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Add detection results to scrollable frame
        for i, result in enumerate(detection_results):
            BackgroundColorDetectionWindow._add_spritesheet_result(
                scrollable_frame, result, i
            )

        # Options explanation
        options_frame = tk.Frame(main_frame)
        options_frame.pack(fill="x", pady=(0, 15))

        options_label = tk.Label(options_frame, text="Options:", font=("Arial", 11, "bold"))
        options_label.pack(anchor="w")

        option_text = (
            "• Apply Color Keying: Make background colors transparent\n"
            "• Exclude Background: Detect sprites while ignoring background colors\n"
            "• Cancel: Skip processing these unknown spritesheets"
        )
        
        options_desc = tk.Label(options_frame, text=option_text, font=("Arial", 9), 
                               justify="left", anchor="w")
        options_desc.pack(fill="x", padx=(10, 0))

        # Button callbacks
        def on_key_background():
            result['action'] = 'key_background'
            dialog.destroy()

        def on_exclude_background():
            result['action'] = 'exclude_background'
            dialog.destroy()

        def on_cancel():
            result['action'] = 'cancel'
            dialog.destroy()

        # Button frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x")

        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, width=12)
        cancel_btn.pack(side="right", padx=(5, 0))

        exclude_btn = tk.Button(button_frame, text="Exclude Background", 
                               command=on_exclude_background, width=16)
        exclude_btn.pack(side="right", padx=(5, 0))

        key_btn = tk.Button(button_frame, text="Apply Color Keying", 
                           command=on_key_background, width=16)
        key_btn.pack(side="right", padx=(5, 0))

        # Set focus and keyboard bindings
        key_btn.focus_set()
        dialog.bind('<Return>', lambda e: on_key_background())
        dialog.bind('<Escape>', lambda e: on_cancel())

        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        dialog.wait_window()

        # Unbind mousewheel when dialog closes
        canvas.unbind_all("<MouseWheel>")

        return result['action']

    @staticmethod
    def _add_spritesheet_result(parent_frame, result, index):
        """
        Add a single spritesheet result to the scrollable frame.

        Args:
            parent_frame: The parent frame to add the result to
            result: Dictionary with spritesheet detection results
            index: Index for alternating row colors
        """
        
        # Row frame with alternating background color
        bg_color = "#f0f0f0" if index % 2 == 0 else "#ffffff"
        row_frame = tk.Frame(parent_frame, bg=bg_color, relief="solid", bd=1)
        row_frame.pack(fill="x", padx=5, pady=2)

        # Filename
        filename_label = tk.Label(row_frame, text=f"📄 {result['filename']}", 
                                 font=("Arial", 10, "bold"), bg=bg_color, anchor="w")
        filename_label.pack(fill="x", padx=10, pady=(5, 2))

        # Colors frame
        colors_frame = tk.Frame(row_frame, bg=bg_color)
        colors_frame.pack(fill="x", padx=20, pady=(0, 5))

        if result['has_transparency']:
            transparency_label = tk.Label(colors_frame, 
                                        text="✓ Image already has transparency", 
                                        font=("Arial", 9), bg=bg_color, fg="green")
            transparency_label.pack(anchor="w")
        else:
            colors_label = tk.Label(colors_frame, text="Detected background colors:", 
                                   font=("Arial", 9), bg=bg_color)
            colors_label.pack(anchor="w")

            # Color samples frame
            for color_index, color in enumerate(result['colors'][:3]):  # Show max 3 colors
                color_sample_frame = tk.Frame(colors_frame, bg=bg_color)
                color_sample_frame.pack(fill="x", pady=1)

                # Color sample (small colored rectangle)
                sample_canvas = tk.Canvas(color_sample_frame, width=20, height=20, 
                                        highlightthickness=1, highlightbackground="black")
                sample_canvas.pack(side="left", padx=(10, 5))
                
                # Create color sample
                hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                sample_canvas.create_rectangle(1, 1, 19, 19, fill=hex_color, outline="")

                # RGB values
                rgb_text = f"RGB({color[0]}, {color[1]}, {color[2]})"
                priority_text = "Primary" if color_index == 0 else f"Secondary {color_index}"
                
                color_info_label = tk.Label(color_sample_frame, 
                                          text=f"{priority_text}: {rgb_text}",
                                          font=("Arial", 9), bg=bg_color)
                color_info_label.pack(side="left")

            # Show if there are more colors
            if len(result['colors']) > 3:
                more_colors_label = tk.Label(colors_frame, 
                                           text=f"... and {len(result['colors']) - 3} more colors",
                                           font=("Arial", 8), bg=bg_color, fg="gray")
                more_colors_label.pack(anchor="w", padx=(10, 0))
