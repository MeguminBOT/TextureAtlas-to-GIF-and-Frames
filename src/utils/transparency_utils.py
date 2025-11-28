"""Transparency visualization utilities for sprite previews.

Provides functions to composite RGBA images over checkerboard or solid
backgrounds, making transparent regions visible in previews.
"""

try:
    from PIL import Image, ImageDraw

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def create_checkerboard_background(
    width: int,
    height: int,
    square_size: int = 8,
    color1: tuple[int, int, int] = (192, 192, 192),
    color2: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image | None:
    """Create a checkerboard pattern for transparency visualization.

    Args:
        width: Width of the background in pixels.
        height: Height of the background in pixels.
        square_size: Size of each checkerboard square in pixels.
        color1: RGB color for odd squares (default light gray).
        color2: RGB color for even squares (default white).

    Returns:
        Checkerboard pattern as an RGB image, or None if PIL unavailable.
    """

    if not PIL_AVAILABLE:
        return None

    img = Image.new("RGB", (width, height), color2)
    draw = ImageDraw.Draw(img)

    for y in range(0, height, square_size):
        for x in range(0, width, square_size):
            if (x // square_size + y // square_size) % 2 == 1:
                draw.rectangle([x, y, x + square_size, y + square_size], fill=color1)

    return img


def composite_with_checkerboard(
    rgba_image: Image.Image,
    square_size: int = 8,
    color1: tuple[int, int, int] = (192, 192, 192),
    color2: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Composite an RGBA image over a checkerboard background.

    Args:
        rgba_image: Image to composite (converted to RGBA if needed).
        square_size: Size of each checkerboard square in pixels.
        color1: RGB color for odd checkerboard squares.
        color2: RGB color for even checkerboard squares.

    Returns:
        RGB image with the input composited over the checkerboard.
    """

    if not PIL_AVAILABLE:
        return rgba_image.convert("RGB") if rgba_image.mode == "RGBA" else rgba_image

    if rgba_image.mode != "RGBA":
        rgba_image = rgba_image.convert("RGBA")

    bg = create_checkerboard_background(
        rgba_image.width, rgba_image.height, square_size, color1, color2
    )
    bg = bg.convert("RGBA")

    result = Image.alpha_composite(bg, rgba_image)
    return result.convert("RGB")


def composite_with_solid_background(
    rgba_image: Image.Image,
    bg_color: tuple[int, int, int] = (127, 127, 127),
) -> Image.Image:
    """Composite an RGBA image over a solid background color.

    Args:
        rgba_image: Image to composite (converted to RGBA if needed).
        bg_color: RGB background color.

    Returns:
        RGB image with the input composited over the solid background.
    """

    if not PIL_AVAILABLE:
        return rgba_image.convert("RGB") if rgba_image.mode == "RGBA" else rgba_image

    if rgba_image.mode != "RGBA":
        rgba_image = rgba_image.convert("RGBA")

    bg = Image.new("RGBA", rgba_image.size, (*bg_color, 255))

    result = Image.alpha_composite(bg, rgba_image)
    return result.convert("RGB")
