import tkinter as tk


class UnknownAtlasWarningWindow:
    """
    A GUI window that displays a warning about unknown atlases and provides options for handling them.

    This window shows a list of detected unknown atlases and explains their limitations,
    then allows the user to choose whether to proceed, skip, or cancel the operation.
    """

    @staticmethod
    def show_warning(parent_window, unknown_atlases):
        """
        Show the unknown atlas warning dialog.

        Args:
            parent_window: The parent tkinter window
            unknown_atlases: List of unknown atlas filenames        Returns:
            str: User's choice - 'proceed', 'skip', or 'cancel'
        """

        unknown_list = "\n".join([f"• {sheet}" for sheet in unknown_atlases[:10]])
        if len(unknown_atlases) > 10:
            unknown_list += f"\n... and {len(unknown_atlases) - 10} more"

        message = (
            f"Warning: {len(unknown_atlases)} unknown atlas type(s) detected:\n\n"
            f"This means either the metadata file is missing or is unsupported.\n"
            f"{unknown_list}\n\n"
            f"The tool can attempt to extract the unknown atlas(es) with these capabilities:\n"
            f"• Automatic sprite detection and extraction\n"
            f"• Smart background color detection and removal\n"
            f"• Precise sprite cropping\n"
            f"• Frame export (animations not supported without metadata)\n"
            f"What would you like to do?"
        )


        dialog = tk.Toplevel(parent_window)
        dialog.title("Unknown Atlas Warning")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.transient(parent_window)
        dialog.grab_set()


        dialog.geometry("+%d+%d" % (
            parent_window.winfo_rootx() + 50,
            parent_window.winfo_rooty() + 50
        ))

        result = {'action': 'cancel'}

        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 15))

        warning_label = tk.Label(title_frame, text="⚠️", font=("Arial", 24))
        warning_label.pack(side="left")
        title_label = tk.Label(title_frame, text="Unknown Atlas Warning", 
                              font=("Arial", 14, "bold"))
        title_label.pack(side="left", padx=(10, 0))

        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True, pady=(0, 20))

        text_widget = tk.Text(text_frame, wrap="word", height=12, width=60)
        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)

        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        text_widget.insert("1.0", message)
        text_widget.config(state="disabled")

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x")

        def on_proceed():
            result['action'] = 'proceed'
            dialog.destroy()

        def on_skip():
            result['action'] = 'skip'
            dialog.destroy()

        def on_cancel():
            result['action'] = 'cancel'
            dialog.destroy()

        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, width=12)
        cancel_btn.pack(side="right", padx=(5, 0))

        skip_btn = tk.Button(button_frame, text="Skip Unknown", command=on_skip, width=12)
        skip_btn.pack(side="right", padx=(5, 0))

        proceed_btn = tk.Button(button_frame, text="Proceed Anyway", command=on_proceed, width=15)
        proceed_btn.pack(side="right", padx=(5, 0))

        proceed_btn.focus_set()
        dialog.bind('<Return>', lambda e: on_proceed())
        dialog.bind('<Escape>', lambda e: on_cancel())
        dialog.wait_window()

        return result['action']
