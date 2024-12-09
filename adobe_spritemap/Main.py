import tkinter as tk
from tkinter import filedialog
from PIL import Image
from Animation import Animation

def browse_directory(entry):
    directory = filedialog.askdirectory()
    entry.delete(0, tk.END)
    entry.insert(0, directory)

def extract_sprites():
    animation_dir = animation_dir_entry.get().replace("\\", "/")
    output_dir = output_dir_entry.get().replace("\\", "/")
    canvas_size = (int(canvas_width_entry.get()), int(canvas_height_entry.get()))
    resample = RESAMPLE_FILTERS[resample_var.get()]
    
    anim = Animation(animation_dir, canvas_size, resample)
    anim.render_to_png_sequence(output_dir=output_dir)

if __name__ == "__main__":
    RESAMPLE_FILTERS = {
        "nearest": Image.NEAREST,
        "bilinear": Image.BILINEAR,
        "bicubic": Image.BICUBIC,
    }

    root = tk.Tk()
    root.title("Adobe Spritemap to PNG (BETA)")

    tk.Label(root, text="Spritemap Directory:").grid(row=0, column=0, padx=10, pady=5)
    animation_dir_entry = tk.Entry(root, width=50)
    animation_dir_entry.grid(row=0, column=1, padx=10, pady=5)
    tk.Button(root, text="Browse", command=lambda: browse_directory(animation_dir_entry)).grid(row=0, column=2, padx=10, pady=5)

    tk.Label(root, text="Output Directory:").grid(row=1, column=0, padx=10, pady=5)
    output_dir_entry = tk.Entry(root, width=50)
    output_dir_entry.grid(row=1, column=1, padx=10, pady=5)
    tk.Button(root, text="Browse", command=lambda: browse_directory(output_dir_entry)).grid(row=1, column=2, padx=10, pady=5)

    tk.Label(root, text="Canvas Width:").grid(row=2, column=0, padx=10, pady=5)
    canvas_width_entry = tk.Entry(root, width=10)
    canvas_width_entry.insert(0, "4096")
    canvas_width_entry.grid(row=2, column=1, padx=10, pady=5, sticky='w')

    tk.Label(root, text="Canvas Height:").grid(row=3, column=0, padx=10, pady=5)
    canvas_height_entry = tk.Entry(root, width=10)
    canvas_height_entry.insert(0, "4096")
    canvas_height_entry.grid(row=3, column=1, padx=10, pady=5, sticky='w')

    tk.Label(root, text="Resample Filter:").grid(row=4, column=0, padx=10, pady=5)
    resample_var = tk.StringVar(value="bicubic")
    resample_menu = tk.OptionMenu(root, resample_var, *RESAMPLE_FILTERS.keys())
    resample_menu.grid(row=4, column=1, padx=10, pady=5, sticky='w')

    tk.Button(root, text="Extract Spritemap", command=extract_sprites).grid(row=5, column=0, columnspan=3, pady=20)

    root.mainloop()