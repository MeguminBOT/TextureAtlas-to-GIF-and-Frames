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
        migrate():
            Migrate existing configuration to include new features and remove obsolete settings.
        merge_defaults(current, defaults):
            Recursively merge current settings with defaults.
        get_extraction_defaults():
            Return a copy of the extraction defaults.
        set_extraction_defaults(**kwargs):
            Update extraction defaults and save.
        get_compression_defaults(format_name=None):
            Get compression defaults for a specific format or all formats.
        set_compression_defaults(format_name, **kwargs):
            Update compression defaults for a specific format.
        get_format_compression_settings(format_name):
            Get compression settings for a specific format in the format expected by the frame exporter.
    """

    DEFAULTS = {
        "language": "auto",  # Language setting: "auto" for system default, or language code like "en", "es", etc.
        "resource_limits": {
            "cpu_cores": "auto",
            "memory_limit_mb": 0,
        },
        "extraction_defaults": {
            "animation_format": "GIF",
            "animation_export": False,
            "fps": 24,
            "delay": 250,
            "period": 0,
            "scale": 1.0,
            "threshold": 0.5,
            "frame_selection": "All",
            "crop_option": "Animation based",
            "filename_format": "Standardized",
            "frame_format": "PNG",
            "frame_export": False,
            "frame_scale": 1.0,
            "variable_delay": False,
            "fnf_idle_loop": False,
        },
        "compression_defaults": {
            "png": {
                "compress_level": 9,
                "optimize": True,
            },
            "webp": {
                "lossless": True,
                "quality": 90,
                "method": 3,
                "alpha_quality": 90,
                "exact": True,
            },
            "avif": {
                "lossless": True,
                "quality": 90,
                "speed": 5,
            },
            "tiff": {
                "compression_type": "lzw",
                "quality": 90,
                "optimize": True,
            },
        },
        "update_settings": {
            "check_updates_on_startup": True,
            "auto_download_updates": False,
        },
        "ui_state": {
            "last_input_directory": "",
            "last_output_directory": "",
            "remember_input_directory": True,
            "remember_output_directory": True,
        },
    }

    TYPE_MAP = {
        "language": str,
        "animation_format": str,
        "animation_export": bool,
        "fps": int,
        "delay": int,
        "period": int,
        "scale": float,
        "threshold": float,
        "crop_option": str,
        "frame_selection": str,
        "filename_format": str,
        "frame_format": str,
        "frame_export": bool,
        "frame_scale": float,
        "variable_delay": bool,
        "fnf_idle_loop": bool,
        "check_updates_on_startup": bool,
        "auto_download_updates": bool,
        "png_compress_level": int,
        "png_optimize": bool,
        "webp_lossless": bool,
        "webp_quality": int,
        "webp_method": int,
        "webp_alpha_quality": int,
        "webp_exact": bool,
        "avif_lossless": bool,
        "avif_quality": int,
        "avif_speed": int,
        "tiff_compression_type": str,
        "tiff_quality": int,
        "tiff_optimize": bool,
        "last_input_directory": str,
        "last_output_directory": str,
        "remember_input_directory": bool,
        "remember_output_directory": bool,
    }

    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "..", "app_config.cfg")
        self.config_path = os.path.abspath(config_path)
        self.settings = dict(self.DEFAULTS)

        if not os.path.isfile(self.config_path):
            print(
                f"[Config] Configuration file not found at '{self.config_path}'. Creating default config..."
            )
            self.save()
        else:
            print(f"[Config] Configuration file found at '{self.config_path}'. Loading settings...")

        self.load()
        self.migrate()

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
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.settings.update(json.load(f))
                print(f"[Config] Configuration loaded successfully from '{self.config_path}'.")
            except Exception as e:
                print(f"[Config] Failed to load configuration: {e}")
                pass

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            print(f"[Config] Configuration saved to '{self.config_path}'.")
        except Exception as e:
            print(f"[Config] Failed to save configuration: {e}")
            pass

    def migrate(self):
        needs_migration = False

        def merge_defaults(current, defaults):
            nonlocal needs_migration
            for key, default_value in defaults.items():
                if key not in current:
                    current[key] = default_value
                    needs_migration = True
                    print(f"[Config] Added new setting '{key}' with default value: {default_value}")
                elif isinstance(default_value, dict) and isinstance(current[key], dict):
                    merge_defaults(current[key], default_value)

            obsolete_keys = []
            for key in current.keys():
                if key not in defaults:
                    obsolete_keys.append(key)
                elif isinstance(defaults[key], dict) and isinstance(current[key], dict):
                    nested_obsolete = []
                    for nested_key in current[key].keys():
                        if nested_key not in defaults[key]:
                            nested_obsolete.append(nested_key)

                    for nested_key in nested_obsolete:
                        del current[key][nested_key]
                        needs_migration = True
                        print(f"[Config] Removed obsolete setting '{key}.{nested_key}'")

            for key in obsolete_keys:
                del current[key]
                needs_migration = True
                print(f"[Config] Removed obsolete setting '{key}'")

        merge_defaults(self.settings, self.DEFAULTS)

        if needs_migration:
            self.save()
            print("[Config] Configuration migration completed successfully.")
        else:
            print("[Config] No migration needed - configuration is up to date.")

    def get(self, key, default=None):
        return self.settings.get(key, default if default is not None else self.DEFAULTS.get(key))

    def set(self, key, value):
        print(f"[Config] Setting '{key}' to: {value}")
        self.settings[key] = value
        self.save()

    def get_compression_defaults(self, format_name=None):
        compression_defaults = self.get(
            "compression_defaults", self.DEFAULTS["compression_defaults"]
        )

        if format_name:
            return dict(compression_defaults.get(format_name, {}))

        return dict(compression_defaults)

    def set_compression_defaults(self, format_name, **kwargs):
        compression_defaults = self.get_compression_defaults()

        if format_name not in compression_defaults:
            compression_defaults[format_name] = {}

        compression_defaults[format_name].update(kwargs)
        self.set("compression_defaults", compression_defaults)

    def get_format_compression_settings(self, format_name):
        format_lower = format_name.lower()
        defaults = self.get_compression_defaults(format_lower)

        if format_lower == "png":
            return {
                "png_compress_level": defaults.get("compress_level", 9),
                "png_optimize": defaults.get("optimize", True),
            }
        elif format_lower == "webp":
            return {
                "webp_lossless": defaults.get("lossless", True),
                "webp_quality": defaults.get("quality", 90),
                "webp_method": defaults.get("method", 3),
                "webp_alpha_quality": defaults.get("alpha_quality", 90),
                "webp_exact": defaults.get("exact", True),
            }
        elif format_lower == "avif":
            return {
                "avif_lossless": defaults.get("lossless", True),
                "avif_quality": defaults.get("quality", 90),
                "avif_speed": defaults.get("speed", 5),
            }
        elif format_lower == "tiff":
            return {
                "tiff_compression_type": defaults.get("compression_type", "lzw"),
                "tiff_quality": defaults.get("quality", 90),
                "tiff_optimize": defaults.get("optimize", True),
            }

        return {}

    def get_last_input_directory(self):
        """Get the last used input directory if remembering is enabled."""
        ui_state = self.settings.get("ui_state", {})
        if ui_state.get("remember_input_directory", True):
            return ui_state.get("last_input_directory", "")
        return ""

    def set_last_input_directory(self, directory):
        """Set the last used input directory and save if remembering is enabled."""
        ui_state = self.settings.get("ui_state", {})
        if ui_state.get("remember_input_directory", True):
            if "ui_state" not in self.settings:
                self.settings["ui_state"] = {}
            self.settings["ui_state"]["last_input_directory"] = directory
            self.save()

    def get_last_output_directory(self):
        """Get the last used output directory if remembering is enabled."""
        ui_state = self.settings.get("ui_state", {})
        if ui_state.get("remember_output_directory", True):
            return ui_state.get("last_output_directory", "")
        return ""

    def set_last_output_directory(self, directory):
        """Set the last used output directory and save if remembering is enabled."""
        ui_state = self.settings.get("ui_state", {})
        if ui_state.get("remember_output_directory", True):
            if "ui_state" not in self.settings:
                self.settings["ui_state"] = {}
            self.settings["ui_state"]["last_output_directory"] = directory
            self.save()

    def get_remember_input_directory(self):
        """Get whether to remember the last input directory."""
        return self.settings.get("ui_state", {}).get("remember_input_directory", True)

    def set_remember_input_directory(self, remember):
        """Set whether to remember the last input directory."""
        if "ui_state" not in self.settings:
            self.settings["ui_state"] = {}
        self.settings["ui_state"]["remember_input_directory"] = remember
        # If disabled, clear the saved directory
        if not remember:
            self.settings["ui_state"]["last_input_directory"] = ""
        self.save()

    def get_remember_output_directory(self):
        """Get whether to remember the last output directory."""
        return self.settings.get("ui_state", {}).get("remember_output_directory", True)

    def set_remember_output_directory(self, remember):
        """Set whether to remember the last output directory."""
        if "ui_state" not in self.settings:
            self.settings["ui_state"] = {}
        self.settings["ui_state"]["remember_output_directory"] = remember
        # If disabled, clear the saved directory
        if not remember:
            self.settings["ui_state"]["last_output_directory"] = ""
        self.save()

    def get_language(self):
        """Get the application language setting."""
        return self.settings.get("language", "auto")

    def set_language(self, language_code):
        """Set the application language."""
        self.settings["language"] = language_code
        self.save()

    def get_effective_language(self):
        """
        Get the effective language code.
        If set to 'auto', returns the system locale, otherwise returns the set language.
        """
        language = self.get_language()
        if language == "auto":
            # Import here to avoid circular imports
            from .translation_manager import get_translation_manager

            manager = get_translation_manager()
            return manager.get_system_locale()
        return language
