import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageSequence

try:
    from PIL.Image import Resampling
    NEAREST = Resampling.NEAREST
except ImportError:
    NEAREST = Image.NEAREST # type: ignore


class AnimationPreviewWindow:
    """
    A window class for previewing animations.

    Methods:
        show(animation_path, settings):
            Opens a preview window for the specified animation file with the given settings.

    Attributes (within the preview window context):
        animation (PIL.Image): The loaded animation image.
        pil_frames (list): List of PIL Image frames extracted from the animation.
        frame_count (int): Total number of frames in the animation.
        durations (list): List of per-frame delays in milliseconds.
        composited_cache (dict): Cache for composited frames with background and scaling applied.
        current_frame (list): Mutable integer tracking the current frame index.
        playing (list): Mutable boolean indicating if playback is active.
        scale_factor (list): Mutable float for the current image scaling factor.
        fixed_size (list): Mutable tuple for the fixed window size after scaling.
        bg_value (tk.IntVar): Tkinter variable for the background color slider.
        tk_img_holder (list): Holds the current Tkinter PhotoImage for display.
    """

    @staticmethod
    def show(animation_path, settings):
        preview_win = tk.Toplevel()

        file_ext = os.path.splitext(animation_path)[1].lower()
        format_name = {".gif": "GIF", ".webp": "WebP"}.get(file_ext, "Animation")

        preview_win.title(f"{format_name} Preview")

        try:
            animation = Image.open(animation_path)

            if file_ext == ".webp":
                pil_frames = []
                try:
                    while True:
                        pil_frames.append(animation.copy())
                        animation.seek(animation.tell() + 1)
                except EOFError:
                    pass
                animation.seek(0)
            else:
                pil_frames = [
                    frame.copy() for frame in ImageSequence.Iterator(animation)
                ]

            frame_count = len(pil_frames)
            current_frame = [0]

            durations = []
            try:
                fps = settings.get("fps", 24)
                delay_setting = settings.get("delay", 250)
                period = settings.get("period", 0)
                var_delay = settings.get("var_delay", False)

                if var_delay:
                    if file_ext == ".webp":
                        for index in range(frame_count):
                            duration = round((index + 1) * 1000 / fps) - round(
                                index * 1000 / fps
                            )
                            durations.append(int(duration))
                    else:
                        for index in range(frame_count):
                            duration = round((index + 1) * 1000 / fps, -1) - round(
                                index * 1000 / fps, -1
                            )
                            durations.append(int(duration))
                else:
                    if file_ext == ".webp":
                        durations = [int(round(1000 / fps))] * frame_count
                    else:
                        durations = [int(round(1000 / fps, -1))] * frame_count

                if durations:
                    if file_ext == ".webp":
                        durations[-1] += int(delay_setting)
                        durations[-1] += max(int(period) - sum(durations), 0)
                    else:
                        durations[-1] += int(delay_setting)
                        durations[-1] += max(int(round(period, -1)) - sum(durations), 0)

            except Exception:
                try:
                    if file_ext == ".webp":
                        animation.seek(0)
                        for i in range(frame_count):
                            try:
                                animation.seek(i)
                                duration = animation.info.get("duration", 0)
                                durations.append(int(duration) if duration else 42)
                            except EOFError:
                                break
                    else:
                        for frame in ImageSequence.Iterator(animation):
                            duration = frame.info.get("duration", 0)
                            durations.append(int(duration) if duration else 42)
                except Exception:
                    pass

        except Exception as e:
            messagebox.showerror("Preview Error", f"Could not load animation file: {e}")
            preview_win.destroy()
            return

        if not durations or len(durations) != frame_count:
            fps = settings.get("fps", 24)
            delay_setting = settings.get("delay", 250)
            base_delay = int(round(1000 / fps, -1))
            durations = [base_delay] * frame_count
            durations[-1] += int(delay_setting)

        frame_counter_label = tk.Label(preview_win, text=f"Frame 0 / {frame_count - 1}")
        frame_counter_label.pack()

        slider_frame = tk.Frame(preview_win)
        slider_frame.pack(pady=4)

        def on_slider(val):
            idx = int(float(val))
            current_frame[0] = idx
            show_frame(idx)

        slider = tk.Scale(
            slider_frame,
            from_=0,
            to=frame_count - 1,
            orient=tk.HORIZONTAL,
            length=300,
            showvalue=False,
            command=on_slider,
        )
        slider.pack()
        slider.set(0)

        preview_win.update_idletasks()
        slider_frame_width = slider_frame.winfo_reqwidth()
        preview_win_width = preview_win.winfo_width()
        if preview_win_width > slider_frame_width:
            slider_frame.pack_configure(
                padx=(preview_win_width - slider_frame_width) // 2
            )

        delays_canvas = tk.Canvas(preview_win, height=40)
        delays_canvas.pack(fill="x", expand=False)
        delays_scrollbar = tk.Scrollbar(
            preview_win, orient="horizontal", command=delays_canvas.xview
        )
        delays_scrollbar.pack(fill="x")
        delays_canvas.configure(xscrollcommand=delays_scrollbar.set)

        delays_frame = tk.Frame(delays_canvas)
        delays_canvas.create_window((0, 0), window=delays_frame, anchor="nw")

        delay_labels = []
        for i, d in enumerate(durations):
            ms = f"{d} ms"
            lbl = tk.Label(delays_frame, text=ms, font=("Arial", 8, "italic"))
            lbl.grid(row=1, column=i, padx=1)
            idx_lbl = tk.Label(delays_frame, text=str(i), font=("Arial", 8))
            idx_lbl.grid(row=0, column=i, padx=1)
            delay_labels.append(lbl)

        delays_frame.update_idletasks()
        delays_canvas.config(scrollregion=delays_canvas.bbox("all"))

        btn_frame = tk.Frame(preview_win)
        btn_frame.pack()
        tk.Button(btn_frame, text="Prev", command=lambda: prev_frame()).pack(
            side=tk.LEFT
        )
        tk.Button(btn_frame, text="Play", command=lambda: play()).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Stop", command=lambda: stop()).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Next", command=lambda: next_frame()).pack(
            side=tk.LEFT
        )

        def open_external(path=animation_path):
            import subprocess
            import platform

            try:
                current_os = platform.system().lower()
                if current_os == "windows":
                    os.startfile(path)
                elif current_os == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    subprocess.Popen(["xdg-open", path])
            except Exception as e:
                messagebox.showerror(
                    "Open External",
                    f"Could not open animation in external program:\n{e}",
                )

        tk.Button(
            btn_frame, text=f"Open {format_name} externally", command=open_external
        ).pack(side=tk.LEFT, padx=(12, 0))

        bg_slider_frame = tk.Frame(preview_win)
        bg_slider_frame.pack(pady=4)
        bg_value = tk.IntVar(value=127)

        def on_bg_change(val):
            clear_cache_for_bg()
            show_frame(current_frame[0])

        tk.Label(bg_slider_frame, text="Background:").pack(side=tk.LEFT, padx=(0, 8))
        bg_slider = tk.Scale(
            bg_slider_frame,
            from_=0,
            to=255,
            orient=tk.HORIZONTAL,
            variable=bg_value,
            command=on_bg_change,
            length=200,
        )
        bg_slider.pack(side=tk.LEFT)

        label = tk.Label(preview_win)
        label.pack()

        composited_cache = {}
        fixed_size = [None]  # type: list[tuple[int, int] | None]
        scale_factor = [1.0]

        def precompute_composited_frames():
            composited_cache.clear()
            bg = bg_value.get()
            scale = scale_factor[0]
            for idx, frame in enumerate(pil_frames):
                img = frame.convert("RGBA")
                if scale != 1.0:
                    new_size = (int(img.width * scale), int(img.height * scale))
                    img = img.resize(new_size, NEAREST)
                bg_img = Image.new("RGBA", img.size, (bg, bg, bg, 255))
                composited = Image.alpha_composite(bg_img, img)
                composited_cache[(idx, bg, scale)] = composited.convert("RGB")

        def get_composited_frame(idx):
            bg = bg_value.get()
            scale = scale_factor[0]
            cache_key = (idx, bg, scale)
            if cache_key in composited_cache:
                return composited_cache[cache_key]
            img = pil_frames[idx].convert("RGBA")
            if scale != 1.0:
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, NEAREST)
            bg_img = Image.new("RGBA", img.size, (bg, bg, bg, 255))
            composited = Image.alpha_composite(bg_img, img)
            composited_cache[cache_key] = composited.convert("RGB")
            return composited_cache[cache_key]

        def clear_cache_for_bg():
            precompute_composited_frames()

        tk_img_holder = [None]  # type: list[ImageTk.PhotoImage | None]

        def show_frame(idx):
            img = get_composited_frame(idx)
            if tk_img_holder[0] is None:
                tk_img = ImageTk.PhotoImage(img)
                label.config(image=tk_img)
                setattr(label, 'image', tk_img)
                tk_img_holder[0] = tk_img
            else:
                tk_img_holder[0].paste(img)
                label.config(image=tk_img_holder[0])
                setattr(label, 'image', tk_img_holder[0])
            frame_counter_label.config(text=f"Frame {idx} / {frame_count - 1}")

            if fixed_size[0] is None:
                extra_height = 240
                width = img.width
                height = img.height + extra_height

                screen_width = preview_win.winfo_screenwidth()
                screen_height = preview_win.winfo_screenheight()

                max_width = int(screen_width * 0.9)
                max_height = int(screen_height * 0.9)

                scale = 1.0
                if width > max_width or height > max_height:
                    scale_w = (max_width) / width
                    scale_h = (max_height) / height
                    scale = min(scale_w, scale_h, 1.0)
                    scale_factor[0] = scale

                    precompute_composited_frames()
                    img2 = get_composited_frame(idx)
                    if tk_img_holder[0] is not None:
                        tk_img_holder[0] = ImageTk.PhotoImage(img2)
                        label.config(image=tk_img_holder[0])
                        setattr(label, 'image', tk_img_holder[0])
                    width = img2.width
                    height = img2.height + extra_height

                preview_win.geometry(f"{width}x{height}")
                preview_win.minsize(width, height)
                fixed_size[0] = (width, height)

            for i, label_widget in enumerate(delay_labels):
                if i == idx:
                    label_widget.config(bg="#e0e0e0")
                else:
                    label_widget.config(bg=preview_win.cget("bg"))

            try:
                label_widget = delay_labels[idx]
                delays_canvas.update_idletasks()

                label_x = label_widget.winfo_x()
                label_w = label_widget.winfo_width()
                canvas_w = delays_canvas.winfo_width()

                scroll_to = max(0, label_x + label_w // 2 - canvas_w // 2)

                scrollregion = delays_canvas.cget("scrollregion")
                if scrollregion:
                    _, _, scrollregion_w, _ = map(int, scrollregion.split())
                    if scrollregion_w > canvas_w:
                        xview = scroll_to / (scrollregion_w - canvas_w)
                        xview = min(max(xview, 0), 1)
                        delays_canvas.xview_moveto(xview)
            except Exception:
                pass

        def next_frame():
            current_frame[0] = (current_frame[0] + 1) % frame_count
            show_frame(current_frame[0])
            slider.set(current_frame[0])

        def prev_frame():
            current_frame[0] = (current_frame[0] - 1) % frame_count
            show_frame(current_frame[0])
            slider.set(current_frame[0])

        playing = [False]

        def play():
            playing[0] = True

            def loop():
                if playing[0]:
                    next_frame()
                    delay = max(1, int(durations[current_frame[0]]))
                    preview_win.after(delay, loop)

            loop()

        def stop():
            playing[0] = False

        precompute_composited_frames()
        show_frame(0)

        def cleanup_temp_animation():
            try:
                animation.close()
                if os.path.isfile(animation_path):
                    os.remove(animation_path)
            except Exception:
                pass
            preview_win.destroy()

        preview_win.protocol("WM_DELETE_WINDOW", cleanup_temp_animation)

        note_text = f"Playback speed of {format_name} animations may not be accurately depicted in this preview window. Open the animation externally for accurate playback."
        note_label = tk.Label(
            preview_win, text=note_text, font=("Arial", 9, "italic"), fg="#333333"
        )
        note_label.pack(side=tk.BOTTOM, pady=(8, 4))

        preview_win.update_idletasks()
        note_width = note_label.winfo_reqwidth()
        win_width = preview_win.winfo_width()
        win_height = preview_win.winfo_height()
        margin = 32
        if note_width + margin > win_width:
            preview_win.geometry(f"{note_width + margin}x{win_height}")
            preview_win.minsize(note_width + margin, win_height)

    @staticmethod
    def preview(
        app,
        name,
        settings_type,
        animation_format_entry,
        fps_entry,
        delay_entry,
        period_entry,
        scale_entry,
        threshold_entry,
        indices_entry,
        frames_entry,
    ):
        settings = {}
        try:
            if animation_format_entry and animation_format_entry.get() != "":
                settings["animation_format"] = animation_format_entry.get()
            if fps_entry.get() != "":
                settings["fps"] = float(fps_entry.get())
            if delay_entry.get() != "":
                settings["delay"] = int(float(delay_entry.get()))
            if period_entry.get() != "":
                settings["period"] = int(float(period_entry.get()))
            if scale_entry.get() != "":
                settings["scale"] = float(scale_entry.get())
            if threshold_entry.get() != "":
                settings["threshold"] = min(max(float(threshold_entry.get()), 0), 1)
            if indices_entry.get() != "":
                indices = [int(ele) for ele in indices_entry.get().split(",")]
                settings["indices"] = indices
        except ValueError as e:
            messagebox.showerror("Invalid input", f"Error: {str(e)}")
            return

        # Check if APNG format is selected and block preview
        animation_format = settings.get("animation_format", "")
        if animation_format == "APNG":
            messagebox.showinfo(
                "Preview Not Available",
                "Preview is not available for APNG format due to display limitations.\n\n"
                "You can still export APNG animations and view them externally.",
            )
            return

        if settings_type == "animation":
            spritesheet_name, animation_name = name.split("/", 1)
        else:
            spritesheet_name = name
            animation_name = None

        input_dir = app.input_dir.get()
        png_path = os.path.join(input_dir, spritesheet_name)
        xml_path = os.path.splitext(png_path)[0] + ".xml"
        txt_path = os.path.splitext(png_path)[0] + ".txt"
        metadata_path = xml_path if os.path.isfile(xml_path) else txt_path

        try:
            from core.extractor import Extractor

            app.update_global_settings()

            extractor = Extractor(None, app.current_version, app.settings_manager)
            animation_path = extractor.generate_temp_animation_for_preview(
                png_path, metadata_path, settings, animation_name, temp_dir=app.temp_dir
            )
            if not animation_path or not os.path.isfile(animation_path):
                messagebox.showerror(
                    "Preview Error", "Could not generate preview animation."
                )
                return
        except Exception as e:
            messagebox.showerror(
                "Preview Error", f"Error generating preview animation: {e}"
            )
            return

        app.show_animation_preview_window(animation_path, settings)
