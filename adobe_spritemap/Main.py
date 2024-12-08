from PIL import Image

# Import our local modules
from Animation import Animation


if __name__ == "__main__":
    RESAMPLE_FILTERS = {
        "nearest": Image.NEAREST,
        "bilinear": Image.BILINEAR,
        "bicubic": Image.BICUBIC,
    }

    animation_dir = r"E:\GitHub\TextureAtlas-to-GIF-and-Frames\testsprite\Spritemap\images\handhank"
    animation_dir_formatted = animation_dir.replace("\\", "/")
    canvas_size = (4000, 4000)
    resample = Image.BICUBIC
    background_color = (0, 0, 0, 0)  # Transparent RGBA

    anim = Animation(animation_dir_formatted, canvas_size, resample)
    anim.render_to_png_sequence(output_dir="./testsprite/Spritemap/testResult")