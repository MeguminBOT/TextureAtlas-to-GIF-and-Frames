import tkinter as tk


class BackgroundKeyingDialog:
    """
    A GUI dialog that prompts the user about background color keying for unknown atlases.

    This dialog appears when an unknown atlas doesn't have transparency and a background
    color is detected, asking the user whether to apply automatic color keying or proceed
    with normal sprite detection that excludes the background color.
    """
    
    _active_dialog = None  # Class variable to track if a dialog is currently open
    _user_choice = None    # Class variable to remember user's choice for batch processing    @staticmethod
    def show_dialog(parent_window, atlas_filename, background_color_info):
        """
        Show the background keying dialog.

        Args:
            parent_window: The parent tkinter window
            atlas_filename: Name of the atlas file being processed
            background_color_info: Either an RGB tuple or a string describing detected colors

        Returns:
            str: User's choice - 'key_background', 'exclude_background', or 'cancel'
        """
          # If a dialog is already active, wait for it to complete
        if BackgroundKeyingDialog._active_dialog is not None:
            try:
                BackgroundKeyingDialog._active_dialog.wait_window()
            except Exception:
                pass  # Dialog may have been closed already
        
        # If user has already made a choice for batch processing, use that choice
        if BackgroundKeyingDialog._user_choice is not None:
            print(f"Using previous user choice: {BackgroundKeyingDialog._user_choice}")
            return BackgroundKeyingDialog._user_choice

        # Handle both single color tuple and multi-color string formats
        if isinstance(background_color_info, tuple):
            color_display = f"RGB {background_color_info}"
        else:
            color_display = str(background_color_info)

        message = (
            f"Atlas: {atlas_filename}\n\n"
            f"This image doesn't have transparency, but the tool detected background color(s):\n"
            f"{color_display}\n\n"
            f"Would you like me to:\n\n"
            f"• Apply Color Keying: Make the background color(s) transparent\n"
            f"• Exclude Background: Detect sprites normally but ignore background color(s)\n"
            f"• Cancel: Skip this atlas entirely\n\n"
            f"Note: If you're processing multiple unknown atlases, your choice will be applied to all remaining ones."
        )

        dialog = tk.Toplevel(parent_window)
        BackgroundKeyingDialog._active_dialog = dialog  # Mark dialog as active
        dialog.title("Background Color Detected")
        dialog.geometry("450x350")
        dialog.resizable(False, False)
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

        info_label = tk.Label(title_frame, text="🎨", font=("Arial", 24))
        info_label.pack(side="left")
        title_label = tk.Label(title_frame, text="Background Color Detected", 
                              font=("Arial", 14, "bold"))
        title_label.pack(side="left", padx=(10, 0))

        # Message text
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True, pady=(0, 20))

        text_widget = tk.Text(text_frame, wrap="word", height=10, width=50)
        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)

        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        text_widget.insert("1.0", message)
        text_widget.config(state="disabled")        # Button callbacks
        def on_key_background():
            result['action'] = 'key_background'
            BackgroundKeyingDialog._user_choice = 'key_background'  # Remember choice for batch processing
            BackgroundKeyingDialog._active_dialog = None
            dialog.destroy()

        def on_exclude_background():
            result['action'] = 'exclude_background'
            BackgroundKeyingDialog._user_choice = 'exclude_background'  # Remember choice for batch processing
            BackgroundKeyingDialog._active_dialog = None
            dialog.destroy()

        def on_cancel():
            result['action'] = 'cancel'
            BackgroundKeyingDialog._user_choice = 'cancel'  # Remember choice for batch processing
            BackgroundKeyingDialog._active_dialog = None
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
        dialog.wait_window()

        return result['action']

    @staticmethod
    def reset_batch_state():
        """
        Reset the batch processing state. Call this at the start of a new batch process
        to ensure the dialog appears for the first unknown atlas encountered.
        """
        BackgroundKeyingDialog._user_choice = None
        BackgroundKeyingDialog._active_dialog = None
        print("Background keying dialog state reset for new batch")
