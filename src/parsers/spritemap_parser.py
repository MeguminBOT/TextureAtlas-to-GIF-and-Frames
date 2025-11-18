#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Parser utilities for Adobe Spritemap Animation.json files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Callable, Set

from utils.utilities import Utilities
from parsers.base_parser import BaseParser, populate_qt_listbox
from core.spritemap.metadata import compute_symbol_lengths, extract_label_ranges


class SpritemapParser(BaseParser):
    """Extract animation names from Adobe Animate spritemap exports."""

    def __init__(self, directory: str, animation_filename: str, listbox_data=None, name_callback: Optional[Callable[[str], None]] = None, filter_single_frame: bool = True):
        super().__init__(directory, animation_filename, name_callback)
        self.listbox_data = listbox_data
        self.filter_single_frame = filter_single_frame

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

            symbol_lengths = compute_symbol_lengths(animation_json)

            for symbol in animation_json.get("SD", {}).get("S", []):
                raw_name = symbol.get("SN")
                if raw_name:
                    if self.filter_single_frame and symbol_lengths.get(raw_name, 0) <= 1:
                        continue
                    names.add(Utilities.strip_trailing_digits(raw_name))

            for label in extract_label_ranges(animation_json, None):
                frame_count = label["end"] - label["start"]
                if self.filter_single_frame and frame_count <= 1:
                    continue
                names.add(label["name"])
        except Exception as exc:
            print(f"Error parsing spritemap animation file {animation_path}: {exc}")
        return names
