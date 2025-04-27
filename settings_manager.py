class SettingsManager:
    """
    A class to manage global, spritesheet, and animation-specific settings.

    Attributes:
        global_settings (dict): Default settings that apply to all sprites and animations.
        spritesheet_settings (dict): Settings specific to individual spritesheets.
        animation_settings (dict): Settings specific to individual animations.

    Methods:
        set_global_settings(**kwargs): Set or update the global settings.
        set_spritesheet_settings(spritesheet_name, **kwargs): Set or update the settings for a specific spritesheet.
        set_animation_settings(animation_name, **kwargs): Set or update the settings for a specific animation.
        get_settings(filename, animation_name=None): Retrieve the settings for a given spritesheet or animation
    """

    def __init__(self):
        self.global_settings = {}
        self.spritesheet_settings = {}
        self.animation_settings = {}

    def set_global_settings(self, **kwargs):
        self.global_settings.update(kwargs)

    def set_spritesheet_settings(self, spritesheet_name, **kwargs):
        if spritesheet_name not in self.spritesheet_settings:
            self.spritesheet_settings[spritesheet_name] = {}

        self.spritesheet_settings[spritesheet_name].update(kwargs)

    def set_animation_settings(self, animation_name, **kwargs):
        if animation_name not in self.animation_settings:
            self.animation_settings[animation_name] = {}

        self.animation_settings[animation_name].update(kwargs)

    def get_settings(self, filename, animation_name=None):
        settings = self.global_settings.copy()

        spritesheet_settings = self.spritesheet_settings.get(filename, {})
        settings.update(spritesheet_settings)

        if animation_name:
            animation_settings = self.animation_settings.get(animation_name, {})
            settings.update(animation_settings)

        return settings