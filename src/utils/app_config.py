import os
import json

class AppConfig:
    """
    A class for managing persistent application configuration settings.

    Attributes:
        DEFAULTS (dict): Default settings for the application.
        TYPE_MAP (dict): Mapping of setting keys to their expected types.
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
        get_extraction_defaults():
            Return a copy of the extraction defaults.
        set_extraction_defaults(**kwargs):
            Update extraction defaults and save.
    """

    DEFAULTS = {
        "resource_limits": {
            "cpu_cores": "auto",
            "memory_limit_mb": 0,
        },
        "extraction_defaults": {
            "animation_format": "None",
            "fps": 24,
            "delay": 250,
            "period": 0,
            "scale": 1.0,
            "threshold": 0.5,
            "keep_frames": "All",
            "crop_option": "Animation based",
            "filename_format": "Standardized",
            "variable_delay": False,
            "fnf_idle_loop": False,
        },
        "update_settings": {
            "check_updates_on_startup": True,
            "auto_download_updates": False,
        },
    }

    TYPE_MAP = {
        "animation_format": str,
        "fps": int,
        "delay": int,
        "period": int,
        "scale": float,
        "threshold": float,
        "crop_option": str,
        "keep_frames": str,
        "filename_format": str,
        "variable_delay": bool,
        "fnf_idle_loop": bool,
        "check_updates_on_startup": bool,
        "auto_download_updates": bool,
    }

    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'app_config.cfg')
        self.config_path = os.path.abspath(config_path)
        self.settings = dict(self.DEFAULTS)

        if not os.path.isfile(self.config_path):
            print(f"[Config] Configuration file not found at '{self.config_path}'. Creating default config...")
            self.save()
        else:
            print(f"[Config] Configuration file found at '{self.config_path}'. Loading settings...")

        self.load()

    def get_extraction_defaults(self):
        return dict(self.get("extraction_defaults", self.DEFAULTS["extraction_defaults"]))

    def set_extraction_defaults(self, **kwargs):
        defaults = self.get_extraction_defaults()
        defaults.update(kwargs)
        self.set("extraction_defaults", defaults)
        self.save()

    def load(self):
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.settings.update(json.load(f))
                print(f"[Config] Configuration loaded successfully from '{self.config_path}'.")
            except Exception as e:
                print(f"[Config] Failed to load configuration: {e}")
                pass

    def save(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            print(f"[Config] Configuration saved to '{self.config_path}'.")
        except Exception as e:
            print(f"[Config] Failed to save configuration: {e}")
            pass

    def get(self, key, default=None):
        return self.settings.get(key, default if default is not None else self.DEFAULTS.get(key))

    def set(self, key, value):
        print(f"[Config] Setting '{key}' to: {value}")
        self.settings[key] = value
        self.save()

