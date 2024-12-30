
class ExtractionConfig:
    """
    A class to manage settings for global, spritesheet, and animation configurations.
    Attributes:
        global_settings (dict): A dictionary containing global settings.
        spritesheet_settings (dict): A dictionary containing settings specific to spritesheets.
        animation_settings (dict): A dictionary containing settings specific to animations.
    Methods:
        get_global_setting(key):
            Retrieves the value of a global setting by key.
        set_global_setting(key, value):
            Sets the value of a global setting by key.
        get_spritesheet_setting(spritesheet, key):
            Retrieves the value of a spritesheet setting by key. If the setting is not found, it falls back to the global setting.
        set_spritesheet_setting(spritesheet, key, value):
            Sets the value of a spritesheet setting by key.
        get_animation_setting(spritesheet, animation, key):
            Retrieves the value of an animation setting by key. If the setting is not found, it falls back to the spritesheet setting, and then to the global setting.
        set_animation_setting(spritesheet, animation, key, value):
            Sets the value of an animation setting by key.
    """

    def __init__(self):
        self.global_settings = {
            'fps': 24,
            'delay': 250,
            'period': 0,
            'scale': 1,
            'threshold': 0.5,
            'indices': [],
            'frames': 'all',
            'crop_option': 'Animation based'
        }
        self.spritesheet_settings = {}
        self.animation_settings = {}

    def get_global_setting(self, key):
        return self.global_settings.get(key)

    def set_global_setting(self, key, value):
        self.global_settings[key] = value

    def get_spritesheet_setting(self, spritesheet, key):
        return self.spritesheet_settings.get(spritesheet, {}).get(key, self.get_global_setting(key))

    def set_spritesheet_setting(self, spritesheet, key, value):
        if spritesheet not in self.spritesheet_settings:
            self.spritesheet_settings[spritesheet] = {}
        self.spritesheet_settings[spritesheet][key] = value

    def get_animation_setting(self, spritesheet, animation, key):
        return self.animation_settings.get(spritesheet, {}).get(animation, {}).get(key, self.get_spritesheet_setting(spritesheet, key))

    def set_animation_setting(self, spritesheet, animation, key, value):
        if spritesheet not in self.animation_settings:
            self.animation_settings[spritesheet] = {}
        if animation not in self.animation_settings[spritesheet]:
            self.animation_settings[spritesheet][animation] = {}
        self.animation_settings[spritesheet][animation][key] = value

    def clear(self):
        self.spritesheet_settings = {}
        self.animation_settings = {}