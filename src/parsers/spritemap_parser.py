#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Parser utilities for Adobe Spritemap Animation.json files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Callable, Set

from utils.utilities import Utilities
from parsers.base_parser import BaseParser, populate_qt_listbox


class SpritemapParser(BaseParser):
    """Extract animation names from Adobe Animate spritemap exports."""

    def __init__(self, directory: str, animation_filename: str, listbox_data=None, name_callback: Optional[Callable[[str], None]] = None):
        super().__init__(directory, animation_filename, name_callback)
        self.listbox_data = listbox_data

    def get_data(self) -> Set[str]:
        names = self.extract_names()
        if self.listbox_data is not None:
            populate_qt_listbox(self.listbox_data, names)
        if self.name_callback:
            for name in names:
                self.name_callback(name)
        return names

    def extract_names(self) -> Set[str]:
        names: Set[str] = set()
        animation_path = Path(self.directory) / self.filename
        try:
            with open(animation_path, "r", encoding="utf-8") as animation_file:
                animation_json = json.load(animation_file)

            for symbol in animation_json.get("SD", {}).get("S", []):
                raw_name = symbol.get("SN")
                if raw_name:
                    names.add(Utilities.strip_trailing_digits(raw_name))

            for layer in animation_json.get("AN", {}).get("TL", {}).get("L", []):
                for frame in layer.get("FR", []):
                    label_name = frame.get("N")
                    if label_name:
                        names.add(label_name)
        except Exception as exc:
            print(f"Error parsing spritemap animation file {animation_path}: {exc}")
        return names
