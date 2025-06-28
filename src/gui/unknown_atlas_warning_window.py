import tkinter as tk
import os

try:
    from PIL import Image, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class UnknownAtlasWarningWindow:
    """
    A GUI window that displays a warning about unknown atlases and provides options for handling them.

    This window shows a list of detected unknown atlases and explains their limitations,
    then allows the user to choose whether to proceed, skip, or cancel the operation.
    """

    @staticmethod
    def show_warning(parent_window, unknown_atlases, input_directory=None):
        """
        Show the unknown atlas warning dialog.

        Args:
            parent_window: The parent tkinter window
            unknown_atlases: List of unknown atlas filenames
            input_directory: Directory containing the atlas files (for thumbnails)

        Returns:
            str: User's choice - 'proceed', 'skip', or 'cancel'
        """

        unknown_list = "\n".join([f"• {sheet}" for sheet in unknown_atlases[:10]])
        if len(unknown_atlases) > 10:
            unknown_list += f"\n... and {len(unknown_atlases) - 10} more"

        dialog = tk.Toplevel(parent_window)
        dialog.title("Unknown Atlas Warning")
        dialog.geometry("600x700")
        dialog.resizable(False, False)
        dialog.transient(parent_window)
        dialog.grab_set()

        dialog.geometry(
            "+%d+%d"
            % (parent_window.winfo_rootx() + 50, parent_window.winfo_rooty() + 50)
        )

        result = {"action": "cancel"}

        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 15))

        warning_label = tk.Label(title_frame, text="⚠️", font=("Arial", 24))
        warning_label.pack(side="left")
        title_label = tk.Label(
            title_frame, text="Unknown Atlas Warning", font=("Arial", 14, "bold")
        )
        title_label.pack(side="left", padx=(10, 0))

        content_frame = tk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True, pady=(0, 20))

        message_text = (
            f"Warning: {len(unknown_atlases)} unknown atlas type(s) detected:\n\n"
            f"This means either the metadata file is missing or is unsupported.\n\n"
            f"The tool can attempt to extract the unknown atlas(es) but has these limitations:\n"
            f"• Animation export is not supported\n"
            f"• Cropping may be inconsistent\n"
            f"• Sprite detection may miss or incorrectly identify sprites\n"
            f"• Output may not be usable in rare cases\n"
            f"What would you like to do?"
        )

        message_label = tk.Label(
            content_frame,
            text=message_text,
            justify="left",
            wraplength=550,
            font=("Arial", 10),
        )
        message_label.pack(anchor="w", pady=(0, 15))

        files_label = tk.Label(
            content_frame, text="Affected files:", font=("Arial", 10, "bold")
        )
        files_label.pack(anchor="w", pady=(0, 5))

        UnknownAtlasWarningWindow._create_thumbnail_section(
            content_frame, unknown_atlases, input_directory
        )

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x")

        def on_proceed():
            result["action"] = "proceed"
            dialog.destroy()

        def on_skip():
            result["action"] = "skip"
            dialog.destroy()

        def on_cancel():
            result["action"] = "cancel"
            dialog.destroy()

        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, width=12)
        cancel_btn.pack(side="right", padx=(5, 0))

        skip_btn = tk.Button(
            button_frame, text="Skip unknown", command=on_skip, width=12
        )
        skip_btn.pack(side="right", padx=(5, 0))

        proceed_btn = tk.Button(
            button_frame, text="Proceed anyway", command=on_proceed, width=15
        )
        proceed_btn.pack(side="right", padx=(5, 0))

        proceed_btn.focus_set()
        dialog.bind("<Return>", lambda e: on_proceed())
        dialog.bind("<Escape>", lambda e: on_cancel())
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.wait_window()

        return result["action"]

    @staticmethod
    def _create_thumbnail_section(parent, unknown_atlases, input_directory):
        thumb_frame = tk.Frame(parent)
        thumb_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(thumb_frame, height=200, bg="white")
        scrollbar = tk.Scrollbar(thumb_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        row = 0
        col = 0
        max_cols = 3

        for i, atlas_name in enumerate(unknown_atlases[:12]):
            thumb_frame_item = tk.Frame(
                scrollable_frame, relief="solid", bd=1, bg="white"
            )
            thumb_frame_item.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            thumbnail = UnknownAtlasWarningWindow._create_thumbnail(
                atlas_name, input_directory
            )

            if thumbnail:
                thumb_label = tk.Label(thumb_frame_item, image=thumbnail, bg="white")
                thumb_label.image = thumbnail
                thumb_label.pack(pady=2)
            else:
                placeholder = tk.Label(
                    thumb_frame_item, text="📷", font=("Arial", 20), bg="white"
                )
                placeholder.pack(pady=2)

            name_label = tk.Label(
                thumb_frame_item,
                text=atlas_name,
                font=("Arial", 8),
                bg="white",
                wraplength=150,
            )
            name_label.pack(pady=2)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        if len(unknown_atlases) > 12:
            more_frame = tk.Frame(scrollable_frame, bg="white")
            more_frame.grid(row=row, column=col, padx=5, pady=5)
            more_label = tk.Label(
                more_frame,
                text=f"... and {len(unknown_atlases) - 12} more",
                font=("Arial", 10, "italic"),
                bg="white",
            )
            more_label.pack(pady=20)

        for i in range(max_cols):
            scrollable_frame.columnconfigure(i, weight=1)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

    @staticmethod
    def _create_thumbnail(filename, input_directory):
        if not PIL_AVAILABLE or not input_directory:
            return None

        try:
            file_path = os.path.join(input_directory, filename)
            if not os.path.exists(file_path):
                return None

            with Image.open(file_path) as img:
                if img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(
                        img,
                        mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None,
                    )
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                img.thumbnail((80, 80), Image.Resampling.LANCZOS)

                return ImageTk.PhotoImage(img)

        except Exception as e:
            print(f"Failed to create thumbnail for {filename}: {e}")
            return None
