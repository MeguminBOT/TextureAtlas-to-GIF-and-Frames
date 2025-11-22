import os
import json
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import QFileDialog

# Import our own modules
from utils.utilities import Utilities


class FnfUtilities:
    """
    A utility class for importing Friday Night Funkin' (FNF) character data.

    Supports characters from:
        Kade Engine, Psych Engine, Codename Engine

    Attributes:
        fnf_char_json_directory (str): Directory path where FNF character data files are stored.

    Methods:
        detect_engine(file_path):
            Attempt to detect the engine character file is from and return the parsed data.
        fnf_load_char_data_settings(settings_manager, data_dict, listbox_png, listbox_data):
            Loads character JSON from the specified directory and updates the settings manager with the correct fps for every animation.
        fnf_select_char_data_directory(settings_manager, data_dict, listbox_png, listbox_data):
            Prompts the user to select a directory containing FNF character JSON files, and loads the data from the selected directory.
    """

    def __init__(self):
        self.fnf_char_json_directory = ""

    def detect_engine(self, file_path):
        if file_path.endswith(".json"):
            with open(file_path, "r") as file:
                try:
                    data = json.load(file)
                    # Check Psych Engine
                    if (
                        "animations" in data
                        and isinstance(data["animations"], list)
                        and all(
                            isinstance(anim, dict)
                            and "name" in anim
                            and "fps" in anim
                            and "anim" in anim
                            and "loop" in anim
                            and "indices" in anim
                            and isinstance(anim["indices"], list)
                            for anim in data["animations"]
                        )
                        and "image" in data
                        and "scale" in data
                        and "flip_x" in data
                        and "no_antialiasing" in data
                    ):
                        return "Psych Engine", data

                    # Check Kade Engine
                    elif (
                        "name" in data
                        and "asset" in data
                        and "startingAnim" in data
                        and "animations" in data
                        and isinstance(data["animations"], list)
                        and all(
                            isinstance(anim, dict)
                            and "name" in anim
                            and "prefix" in anim
                            and "offsets" in anim
                            and isinstance(anim["offsets"], list)
                            and len(anim["offsets"]) == 2
                            and (
                                "frameIndices" not in anim or isinstance(anim["frameIndices"], list)
                            )
                            and ("looped" not in anim or isinstance(anim["looped"], bool))
                            for anim in data["animations"]
                        )
                    ):
                        return "Kade Engine", data
                except json.JSONDecodeError:
                    pass

        elif file_path.endswith(".xml"):
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                # Check Codename Engine
                if root.tag == "character" and all(
                    anim.tag == "anim"
                    and "name" in anim.attrib
                    and "anim" in anim.attrib
                    and "fps" in anim.attrib
                    and "loop" in anim.attrib
                    and ("indices" not in anim.attrib or ".." in anim.attrib["indices"])
                    for anim in root.findall("anim")
                ):
                    scale = root.attrib.get("scale")
                    antialiasing = root.attrib.get("antialiasing")
                    if scale is not None:
                        root.attrib["scale"] = scale
                    if antialiasing is not None:
                        root.attrib["antialiasing"] = antialiasing
                    return "Codename Engine", root
            except ET.ParseError:
                pass
        return "Unknown", None

    def fnf_load_char_data_settings(self, settings_manager, data_dict, listbox_png_callback=None, listbox_data_callback=None):
        """
        Load FNF character data settings using callbacks for UI updates.
        
        Args:
            settings_manager: Settings manager instance
            data_dict: Data dictionary to update
            listbox_png_callback: Callback to add PNG items to UI (optional)
            listbox_data_callback: Callback to add data items to UI (optional)
        """
        if not self.fnf_char_json_directory:
            return

        for filename in os.listdir(self.fnf_char_json_directory):
            file_path = os.path.join(self.fnf_char_json_directory, filename)
            self._process_character_file(
                file_path,
                settings_manager,
                data_dict=data_dict,
                listbox_png_callback=listbox_png_callback,
                listbox_data_callback=listbox_data_callback,
            )

    def fnf_select_char_data_directory(
        self, settings_manager, data_dict, listbox_png_callback=None, listbox_data_callback=None, parent_window=None
    ):
        """
        Select FNF character data directory using Qt file dialog.
        
        Args:
            settings_manager: Settings manager instance
            data_dict: Data dictionary
            listbox_png_callback: Callback to add PNG items to UI (optional)
            listbox_data_callback: Callback to add data items to UI (optional)
            parent_window: Parent Qt window for the dialog
        """
        directory = QFileDialog.getExistingDirectory(
            parent_window,
            "Select FNF Character Data Directory"
        )
        if directory:
            self.fnf_char_json_directory = directory
            self.fnf_load_char_data_settings(settings_manager, data_dict, listbox_png_callback, listbox_data_callback)
            print("Animation settings updated in SettingsManager.")

    def import_character_settings(self, file_path, settings_manager):
        """Import a single FNF character definition and store settings (including offsets)."""
        processed = self._process_character_file(file_path, settings_manager)
        if not processed:
            raise ValueError("Unsupported or invalid FNF character data file.")

    def _process_character_file(
        self,
        file_path,
        settings_manager,
        data_dict=None,
        listbox_png_callback=None,
        listbox_data_callback=None,
    ):
        if not file_path or not os.path.exists(file_path):
            return False

        engine_type, parsed_data = self.detect_engine(file_path)
        filename = os.path.basename(file_path)
        print(f"Found {engine_type} data for {filename}.")

        if engine_type == "Psych Engine" and parsed_data:
            png_filename = self._register_spritesheet_entry(
                parsed_data.get("image", ""),
                file_path,
                data_dict,
                listbox_png_callback,
                listbox_data_callback,
            )
            scale = parsed_data.get("scale", 1)
            for anim in parsed_data.get("animations", []):
                anim_name = Utilities.strip_trailing_digits(anim.get("name", ""))
                fps = anim.get("fps", 0)
                indices = anim.get("indices") or None
                loop = bool(anim.get("loop", False))
                offsets = anim.get("offsets")
                self._update_animation_settings(
                    settings_manager,
                    png_filename,
                    anim_name,
                    fps,
                    indices=indices,
                    loop=loop,
                    scale=scale,
                    offsets=offsets,
                    flip_x=parsed_data.get("flip_x", False),
                )
            return True

        if engine_type == "Codename Engine" and parsed_data is not None:
            png_filename = self._register_spritesheet_entry(
                filename,
                file_path,
                data_dict,
                listbox_png_callback,
                listbox_data_callback,
            )
            try:
                scale = float(parsed_data.attrib.get("scale", 1))
            except (TypeError, ValueError):
                scale = 1
            for anim in parsed_data.findall("anim"):
                anim_name = Utilities.strip_trailing_digits(anim.get("name", ""))
                fps = int(anim.get("fps", 0))
                indices = self._parse_indices_attribute(anim.get("indices"))
                loop = anim.get("loop", "false").lower() == "true"
                offsets = self._parse_xml_offsets(anim)
                self._update_animation_settings(
                    settings_manager,
                    png_filename,
                    anim_name,
                    fps,
                    indices=indices,
                    loop=loop,
                    scale=scale,
                    offsets=offsets,
                )
            return True

        if engine_type == "Kade Engine" and parsed_data:
            png_filename = self._register_spritesheet_entry(
                filename,
                file_path,
                data_dict,
                listbox_png_callback,
                listbox_data_callback,
            )
            fps = parsed_data.get("frameRate", 0)
            scale_value = parsed_data.get("scale", 1)
            for anim in parsed_data.get("animations", []):
                anim_name = Utilities.strip_trailing_digits(anim.get("name", ""))
                indices = anim.get("frameIndices") or None
                loop = bool(anim.get("looped", False))
                offsets = anim.get("offsets")
                self._update_animation_settings(
                    settings_manager,
                    png_filename,
                    anim_name,
                    fps,
                    indices=indices,
                    loop=loop,
                    scale=scale_value,
                    offsets=offsets,
                )
            return True

        print(f"Skipping {filename}: Not a FNF character data file or unsupported engine type.")
        return False

    def _register_spritesheet_entry(
        self,
        image_hint,
        file_path,
        data_dict=None,
        listbox_png_callback=None,
        listbox_data_callback=None,
    ):
        base_name = image_hint or os.path.splitext(os.path.basename(file_path))[0]
        png_base = os.path.splitext(os.path.basename(base_name))[0]
        png_filename = f"{png_base}.png"

        if data_dict is not None and png_filename not in data_dict:
            data_dict[png_filename] = file_path
            if listbox_png_callback:
                listbox_png_callback(png_filename)
        if listbox_data_callback:
            listbox_data_callback(file_path)
        return png_filename

    @staticmethod
    def _offsets_to_alignment(offsets, scale=1.0, flip_x=False):
        if not isinstance(offsets, (list, tuple)) or len(offsets) != 2:
            return None
        try:
            x_val = int(offsets[0])
            y_val = int(offsets[1])
        except (TypeError, ValueError):
            return None
        payload = {"default": {"x": -x_val, "y": -y_val}, "frames": {}}
        raw_block = {"default": {"x": x_val, "y": y_val}, "frames": {}}
        try:
            scale_value = float(scale)
        except (TypeError, ValueError):
            scale_value = 1.0
        raw_block["scale"] = scale_value
        if flip_x:
            raw_block["flip_x"] = bool(flip_x)
        payload["_fnf_raw_offsets"] = raw_block
        payload["origin_mode"] = "top_left"
        return payload

    @staticmethod
    def _parse_indices_attribute(raw_indices):
        if not raw_indices:
            return None
        if ".." in raw_indices:
            return [int(i) for i in raw_indices.split("..")]
        return [int(i.strip()) for i in raw_indices.split(",") if i.strip()]

    @staticmethod
    def _parse_xml_offsets(anim_element):
        raw = anim_element.attrib.get("offset") or anim_element.attrib.get("offsets")
        if not raw:
            return None
        parts = [part.strip() for part in raw.replace(" ", "").split(",") if part.strip()]
        if len(parts) != 2:
            return None
        try:
            return [int(parts[0]), int(parts[1])]
        except (TypeError, ValueError):
            return None

    def _update_animation_settings(
        self,
        settings_manager,
        png_filename,
        anim_name,
        fps,
        indices=None,
        loop=False,
        scale=1,
        offsets=None,
        flip_x=False,
    ):
        if not settings_manager or not png_filename or not anim_name:
            return

        full_anim_name = f"{png_filename}/{anim_name}"
        settings = {"fps": fps}

        if scale not in (None, 1):
            settings["scale"] = scale
        if indices:
            settings["indices"] = indices
        if loop:
            settings["delay"] = 0

        alignment = self._offsets_to_alignment(offsets, scale=scale, flip_x=flip_x)
        if alignment:
            settings["alignment_overrides"] = alignment

        settings_manager.set_animation_settings(full_anim_name, **settings)
