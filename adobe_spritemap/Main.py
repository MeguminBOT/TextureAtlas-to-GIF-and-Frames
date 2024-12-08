from PIL import Image

# Import our local modules
from Animation import Animation


if __name__ == "__main__":
    RESAMPLE_FILTERS = {
        "nearest": Image.NEAREST,
        "bilinear": Image.BILINEAR,
        "bicubic": Image.BICUBIC,
    }

    animation_dir = r"E:\GitHub\TextureAtlas-to-GIF-and-Frames\experimental features\Atlas\madness v1.1\assets\shared\images\characters\hank"
    animation_dir_formatted = animation_dir.replace("\\", "/")
    animation_dir = "./test2"
    canvas_size = (4000, 4000)
    resample = Image.BICUBIC
    background_color = (0, 0, 0, 0)  # Transparent RGBA

    anim = Animation(animation_dir_formatted, canvas_size, resample)
    anim.render_to_png_sequence(output_dir="./testResult")