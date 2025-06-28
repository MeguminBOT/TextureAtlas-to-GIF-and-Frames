import tkinter as tk
from tkinter import ttk


class BackgroundHandlerWindow:
    """
    A class that handles background color detection and keying options for unknown spritesheets.

    This window displays detected background colors for unknown spritesheets with individual checkboxes
    to control whether background removal should be applied to each spritesheet.
    """

    @staticmethod
    def show_background_options(parent_window, detection_results):
        """
        Show the background handling options dialog with individual controls.

        Args:
            parent_window: The parent tkinter window
            detection_results: List of dictionaries with keys:
                - 'filename': Name of the spritesheet file
                - 'colors': List of RGB tuples for detected background colors
                - 'has_transparency': Boolean indicating if image already has transparency

        Returns:
            dict: Dictionary mapping filenames to their background handling choice:
                - 'key_background': Apply color keying (remove background)
                - 'exclude_background': Exclude background during sprite detection
                - 'skip': Skip processing this file
        """
        
        print(f"[BackgroundHandlerWindow] Called with {len(detection_results)} detection results")
        
        if not detection_results:
            print("[BackgroundHandlerWindow] No detection results, returning empty dict")
            return {}

        print("[BackgroundHandlerWindow] Creating dialog window...")
        dialog = tk.Toplevel(parent_window)
        dialog.title("Background Color Options")
        dialog.geometry("800x600")
        dialog.resizable(True, True)
        dialog.transient(parent_window)
        dialog.grab_set()

        # Center the dialog relative to parent window
        dialog.geometry(
            "+%d+%d"
            % (parent_window.winfo_rootx() + 50, parent_window.winfo_rooty() + 50)
        )

        result = {}
        checkbox_vars = {}
        print("[BackgroundHandlerWindow] Dialog setup complete, entering main loop...")

        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        # Title frame with icon
        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 15))

        warning_label = tk.Label(title_frame, text="🎨", font=("Arial", 24))
        warning_label.pack(side="left")
        title_label = tk.Label(
            title_frame, text="Background Color Options", font=("Arial", 14, "bold")
        )
        title_label.pack(side="left", padx=(10, 0))

        # Description
        description = (
            f"Found {len(detection_results)} unknown spritesheet(s) with background colors.\n"
            f"Check the box next to each file to remove its background color during processing:"
        )

        desc_label = tk.Label(
            main_frame,
            text=description,
            font=("Arial", 10),
            justify="left",
            wraplength=750,
        )
        desc_label.pack(fill="x", pady=(0, 10))

        # Global controls frame
        global_frame = tk.Frame(main_frame)
        global_frame.pack(fill="x", pady=(0, 10))

        def select_all():
            for var in checkbox_vars.values():
                var.set(True)

        def select_none():
            for var in checkbox_vars.values():
                var.set(False)

        select_all_btn = tk.Button(
            global_frame, text="Select All", command=select_all, width=12
        )
        select_all_btn.pack(side="left", padx=(0, 5))

        select_none_btn = tk.Button(
            global_frame, text="Select None", command=select_none, width=12
        )
        select_none_btn.pack(side="left")

        # Scrollable frame for the detection results
        canvas_frame = tk.Frame(main_frame)
        canvas_frame.pack(fill="both", expand=True, pady=(0, 15))

        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Add detection results to scrollable frame
        for i, result in enumerate(detection_results):
            checkbox_var = tk.BooleanVar(value=True)  # Default to checked
            checkbox_vars[result["filename"]] = checkbox_var
            BackgroundHandlerWindow._add_spritesheet_entry(
                scrollable_frame, result, i, checkbox_var
            )

        # Options explanation
        options_frame = tk.Frame(main_frame)
        options_frame.pack(fill="x", pady=(0, 15))

        options_label = tk.Label(
            options_frame, text="Processing Options:", font=("Arial", 11, "bold")
        )
        options_label.pack(anchor="w")

        option_text = (
            "• Checked: Remove background colors (apply color keying)\n"
            "• Unchecked: Keep background colors but exclude them during sprite detection"
        )

        options_desc = tk.Label(
            options_frame,
            text=option_text,
            font=("Arial", 9),
            justify="left",
            anchor="w",
        )
        options_desc.pack(fill="x", padx=(10, 0))

        # Button callbacks
        def on_apply():
            for filename, var in checkbox_vars.items():
                if var.get():
                    result[filename] = "key_background"
                else:
                    result[filename] = "exclude_background"
            dialog.destroy()

        def on_cancel():
            for filename in checkbox_vars.keys():
                result[filename] = "skip"
            dialog.destroy()

        # Button frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x")

        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, width=12)
        cancel_btn.pack(side="right", padx=(5, 0))

        apply_btn = tk.Button(
            button_frame, text="Apply Settings", command=on_apply, width=16
        )
        apply_btn.pack(side="right", padx=(5, 0))

        # Set focus and keyboard bindings
        apply_btn.focus_set()
        dialog.bind("<Return>", lambda e: on_apply())
        dialog.bind("<Escape>", lambda e: on_cancel())

        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        dialog.wait_window()

        # Unbind mousewheel when dialog closes
        canvas.unbind_all("<MouseWheel>")

        return result

    @staticmethod
    def _add_spritesheet_entry(parent_frame, result, index, checkbox_var):
        """
        Add a single spritesheet entry with checkbox to the scrollable frame.

        Args:
            parent_frame: The parent frame to add the entry to
            result: Dictionary with spritesheet detection results
            index: Index for alternating row colors
            checkbox_var: BooleanVar for the checkbox state
        """

        # Row frame with alternating background color
        bg_color = "#f0f0f0" if index % 2 == 0 else "#ffffff"
        row_frame = tk.Frame(parent_frame, bg=bg_color, relief="solid", bd=1)
        row_frame.pack(fill="x", padx=5, pady=2)

        # Header frame with checkbox and filename
        header_frame = tk.Frame(row_frame, bg=bg_color)
        header_frame.pack(fill="x", padx=10, pady=(5, 2))

        # Checkbox for this spritesheet
        checkbox = tk.Checkbutton(header_frame, variable=checkbox_var, bg=bg_color)
        checkbox.pack(side="left")

        # Filename
        filename_label = tk.Label(
            header_frame,
            text=f"📄 {result['filename']}",
            font=("Arial", 10, "bold"),
            bg=bg_color,
            anchor="w",
        )
        filename_label.pack(side="left", padx=(5, 0))

        # Colors frame
        colors_frame = tk.Frame(row_frame, bg=bg_color)
        colors_frame.pack(fill="x", padx=30, pady=(0, 5))

        if result["has_transparency"]:
            transparency_label = tk.Label(
                colors_frame,
                text="✓ Image already has transparency",
                font=("Arial", 9),
                bg=bg_color,
                fg="green",
            )
            transparency_label.pack(anchor="w")
        else:
            colors_label = tk.Label(
                colors_frame,
                text="Detected background colors:",
                font=("Arial", 9),
                bg=bg_color,
            )
            colors_label.pack(anchor="w")

            # Color samples frame
            for color_index, color in enumerate(
                result["colors"][:3]
            ):  # Show max 3 colors
                color_sample_frame = tk.Frame(colors_frame, bg=bg_color)
                color_sample_frame.pack(fill="x", pady=1)

                # Color sample (small colored rectangle)
                sample_canvas = tk.Canvas(
                    color_sample_frame,
                    width=20,
                    height=20,
                    highlightthickness=1,
                    highlightbackground="black",
                )
                sample_canvas.pack(side="left", padx=(10, 5))

                # Create color sample
                hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                sample_canvas.create_rectangle(1, 1, 19, 19, fill=hex_color, outline="")

                # RGB values
                rgb_text = f"RGB({color[0]}, {color[1]}, {color[2]})"
                priority_text = (
                    "Primary" if color_index == 0 else f"Secondary {color_index}"
                )

                color_info_label = tk.Label(
                    color_sample_frame,
                    text=f"{priority_text}: {rgb_text}",
                    font=("Arial", 9),
                    bg=bg_color,
                )
                color_info_label.pack(side="left")

            # Show if there are more colors
            if len(result["colors"]) > 3:
                more_colors_label = tk.Label(
                    colors_frame,
                    text=f"... and {len(result['colors']) - 3} more colors",
                    font=("Arial", 8),
                    bg=bg_color,
                    fg="gray",
                )
                more_colors_label.pack(anchor="w", padx=(10, 0))

    @staticmethod
    def reset_batch_state():
        """
        Reset any batch processing state. 
        Provided for compatibility with existing code.
        """
        # Clear any previous file choices
        if hasattr(BackgroundHandlerWindow, '_file_choices'):
            BackgroundHandlerWindow._file_choices = {}
        print("[BackgroundHandlerWindow] Batch state reset for new processing")
