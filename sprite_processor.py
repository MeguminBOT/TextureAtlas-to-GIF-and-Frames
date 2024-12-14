from PIL import Image
from wand.image import Image as WandImg

from utilities import Utilities

class SpriteProcessor:
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