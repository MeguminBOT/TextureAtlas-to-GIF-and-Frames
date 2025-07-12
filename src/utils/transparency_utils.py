#!/usr/bin/env python3
# -*- coding: utf-8 -*-

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def create_checkerboard_background(width, height, square_size=8, color1=(192, 192, 192), color2=(255, 255, 255)):
    """
    Create a checkerboard pattern background for transparency visualization.
    
    Args:
        width (int): Width of the background
        height (int): Height of the background
        square_size (int): Size of each checkerboard square
        color1 (tuple): RGB color for first checkerboard color (default light gray)
        color2 (tuple): RGB color for second checkerboard color (default white)
        
    Returns:
        PIL.Image: Checkerboard pattern image
    """
    if not PIL_AVAILABLE:
        return None
        
    # Create new RGB image
    img = Image.new("RGB", (width, height), color2)
    draw = ImageDraw.Draw(img)
    
    # Draw checkerboard pattern
    for y in range(0, height, square_size):
        for x in range(0, width, square_size):
            # Determine if this square should be color1 or color2
            if (x // square_size + y // square_size) % 2 == 1:
                draw.rectangle([x, y, x + square_size, y + square_size], fill=color1)
    
    return img


def composite_with_checkerboard(rgba_image, square_size=8, color1=(192, 192, 192), color2=(255, 255, 255)):
    """
    Composite an RGBA image over a checkerboard background.
    
    Args:
        rgba_image (PIL.Image): RGBA image to composite
        square_size (int): Size of each checkerboard square
        color1 (tuple): RGB color for first checkerboard color
        color2 (tuple): RGB color for second checkerboard color
        
    Returns:
        PIL.Image: RGB image with checkerboard background
    """
    if not PIL_AVAILABLE:
        return rgba_image.convert("RGB") if rgba_image.mode == "RGBA" else rgba_image
    
    # Ensure input is RGBA
    if rgba_image.mode != "RGBA":
        rgba_image = rgba_image.convert("RGBA")
    
    # Create checkerboard background
    bg = create_checkerboard_background(rgba_image.width, rgba_image.height, square_size, color1, color2)
    bg = bg.convert("RGBA")
    
    # Composite the RGBA image over the checkerboard
    result = Image.alpha_composite(bg, rgba_image)
    return result.convert("RGB")


def composite_with_solid_background(rgba_image, bg_color=(127, 127, 127)):
    """
    Composite an RGBA image over a solid background color.
    
    Args:
        rgba_image (PIL.Image): RGBA image to composite
        bg_color (tuple): RGB background color
        
    Returns:
        PIL.Image: RGB image with solid background
    """
    if not PIL_AVAILABLE:
        return rgba_image.convert("RGB") if rgba_image.mode == "RGBA" else rgba_image
    
    # Ensure input is RGBA
    if rgba_image.mode != "RGBA":
        rgba_image = rgba_image.convert("RGBA")
    
    # Create solid background
    bg = Image.new("RGBA", rgba_image.size, (*bg_color, 255))
    
    # Composite the RGBA image over the solid background
    result = Image.alpha_composite(bg, rgba_image)
    return result.convert("RGB")
