import os
import json

class AppConfig:
    """
    A class for managing persistent application configuration settings.

    Attributes:
        config_path (str): Path to the JSON config file.
        settings (dict): Dictionary of current settings.

    Methods:
        load():
            Load settings from the config file, or use defaults if not found.
        save():
            Save current settings to the config file.
        get(key, default=None):
            Retrieve a setting value by key, with optional default.
        set(key, value):
            Set a setting value and immediately save to disk.
    """

    DEFAULTS = {
        "cpu_cores": "auto",
        "memory_limit_mb": 0,
    }

    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'app_config.cfg')
        self.config_path = os.path.abspath(config_path)
        self.settings = dict(self.DEFAULTS)
        self.load()

    def load(self):
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.settings.update(json.load(f))
            except Exception:
                pass

    def save(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.settings.get(key, default if default is not None else self.DEFAULTS.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()
