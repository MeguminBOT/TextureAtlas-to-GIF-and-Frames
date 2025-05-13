from PIL import Image

# Import our own modules
from utils.utilities import Utilities

class SpriteProcessor:
    """
    A class for processing sprite data from an atlas image.

    Attributes:
        atlas (PIL.Image.Image):
            The atlas image containing all the sprites.
        sprites (list of dict):
            A list of sprite metadata dictionaries, each containing the following keys:
                - 'name' (str): The name of the sprite.
                - 'x', 'y' (int): The top-left coordinates of the sprite in the atlas.
                - 'width', 'height' (int): The dimensions of the sprite in the atlas.
                - 'frameX', 'frameY' (int, optional): The x and y offset for the frame. Defaults to 0.
                - 'frameWidth', 'frameHeight' (int, optional): The width and height of the final frame. Defaults to the sprite's dimensions.
                - 'rotated' (bool, optional): Indicates if the sprite is rotated 90 degrees clockwise in the atlas. Defaults to False.

    Methods:
        process_sprites() -> dict:
            Processes the sprites in the atlas and returns a dictionary of animations.
            Each animation is a mapping of folder names to lists of sprite data. Sprite data includes:
                - Name of the sprite.
                - Processed frame image (PIL.Image.Image).
                - Sprite's original metadata (tuple of x, y, width, height, frameX, frameY).
    """

    def __init__(self, atlas, sprites):
        self.atlas = atlas
        self.sprites = sprites

    def process_sprites(self):
        animations = {}
        for sprite in self.sprites:
            name = sprite['name']
            x, y, width, height = sprite['x'], sprite['y'], sprite['width'], sprite['height']
            frameX = sprite.get('frameX', 0)
            frameY = sprite.get('frameY', 0)
            frameWidth = sprite.get('frameWidth', width)
            frameHeight = sprite.get('frameHeight', height)
            rotated = sprite.get('rotated', False)

            print(f"Processing sprite: {name}")
            
            sprite_image = self.atlas.crop((x, y, x + width, y + height))
            if rotated:
                sprite_image = sprite_image.rotate(90, expand=True)
                frameWidth = max(height-frameX, frameWidth, 1)
                frameHeight = max(width-frameY, frameHeight, 1)
            else:
                frameWidth = max(width-frameX, frameWidth, 1)
                frameHeight = max(height-frameY, frameHeight, 1)

            frame_image = Image.new('RGBA', (frameWidth, frameHeight))
            frame_image.paste(sprite_image, (-frameX, -frameY))
            if frame_image.mode != 'RGBA':
                frame_image = frame_image.convert('RGBA')

            folder_name = Utilities.strip_trailing_digits(name)
            animations.setdefault(folder_name, []).append((name, frame_image, (x, y, width, height, frameX, frameY)))
        return animations