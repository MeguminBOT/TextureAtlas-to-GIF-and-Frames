from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Sequence

from PIL import Image

from gui.extractor.background_handler_window import BackgroundHandlerWindow
from parsers.unknown_parser import UnknownParser


class UnknownSpritesheetHandler:
    """Encapsulates background detection flows for unknown spritesheets."""

    SUPPORTED_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")

    def __init__(self, logger: Callable[[str], None] | None = None):
        self._log = logger or print

    def handle_background_detection(
        self,
        input_dir: str,
        spritesheet_list: Sequence[str],
        parent_window,
    ) -> bool:
        """Run detection workflow. Returns True if user cancels extraction."""
        try:
            self._log(
                f"[UnknownSpritesheetHandler] Checking {len(spritesheet_list)} spritesheets for unknown files..."
            )
            base_directory = Path(input_dir)
            unknown_sheets = self._collect_unknown_spritesheets(
                base_directory, spritesheet_list
            )
            if not unknown_sheets:
                self._log("[UnknownSpritesheetHandler] No unknown spritesheets found")
                return False

            self._log(
                f"[UnknownSpritesheetHandler] Found {len(unknown_sheets)} unknown spritesheet(s), checking for background colors..."
            )
            BackgroundHandlerWindow.reset_batch_state()

            detection_results = self._detect_background_colors(
                base_directory, unknown_sheets
            )
            self._log(
                f"[UnknownSpritesheetHandler] Detection results: {len(detection_results)} entries"
            )
            for result in detection_results:
                self._log(
                    f"  - {result['filename']}: {len(result['colors'])} colors, transparency: {result['has_transparency']}"
                )

            needs_background_handling = any(
                (not result["has_transparency"]) and result["colors"]
                for result in detection_results
            )

            if detection_results and needs_background_handling:
                self._log(
                    "[UnknownSpritesheetHandler] Some images have backgrounds that need handling - showing background handler window..."
                )
                background_choices = BackgroundHandlerWindow.show_background_options(
                    parent_window, detection_results
                )
                self._log(
                    f"[UnknownSpritesheetHandler] User choices: {background_choices}"
                )

                if background_choices.get("_cancelled", False):
                    self._log(
                        "[UnknownSpritesheetHandler] Background handler was cancelled by user - stopping extraction"
                    )
                    return True

                if background_choices:
                    if not hasattr(BackgroundHandlerWindow, "_file_choices"):
                        BackgroundHandlerWindow._file_choices = {}
                    BackgroundHandlerWindow._file_choices.update(background_choices)
                    self._log(
                        f"[UnknownSpritesheetHandler] Background handling preferences set for {len(background_choices)} files"
                    )
            elif detection_results:
                self._log(
                    "[UnknownSpritesheetHandler] All images either have transparency or no detectable backgrounds - skipping background handler window"
                )
            else:
                self._log("[UnknownSpritesheetHandler] No detection results to show")

        except Exception as exc:
            self._log(
                f"[UnknownSpritesheetHandler] Error in background color detection: {exc}"
            )

        return False

    def _collect_unknown_spritesheets(
        self, base_directory: Path, spritesheet_list: Sequence[str]
    ) -> List[str]:
        unknown_sheets: List[str] = []
        for filename in spritesheet_list:
            relative_path = Path(filename)
            atlas_path = base_directory / relative_path
            base_filename = relative_path.stem
            atlas_dir = atlas_path.parent

            xml_path = atlas_dir / f"{base_filename}.xml"
            txt_path = atlas_dir / f"{base_filename}.txt"
            spritemap_json_path = atlas_dir / f"{base_filename}.json"
            animation_json_path = atlas_dir / "Animation.json"
            has_spritemap_metadata = (
                animation_json_path.is_file() and spritemap_json_path.is_file()
            )

            if (
                not xml_path.is_file()
                and not txt_path.is_file()
                and not has_spritemap_metadata
                and atlas_path.is_file()
                and atlas_path.suffix.lower() in self.SUPPORTED_IMAGE_SUFFIXES
            ):
                unknown_sheets.append(filename)
                self._log(
                    f"[UnknownSpritesheetHandler] Found unknown spritesheet: {filename}"
                )
        return unknown_sheets

    def _detect_background_colors(
        self, base_directory: Path, unknown_sheets: Sequence[str]
    ):
        detection_results = []
        for filename in unknown_sheets:
            image_path = str(base_directory / Path(filename))
            try:
                image = Image.open(image_path)
                if image.mode != "RGBA":
                    image = image.convert("RGBA")

                has_transparency = UnknownParser._has_transparency(image)
                detected_colors = []
                if not has_transparency:
                    detected_colors = UnknownParser._detect_background_colors(
                        image, max_colors=3
                    )

                detection_results.append(
                    {
                        "filename": filename,
                        "colors": detected_colors,
                        "has_transparency": has_transparency,
                    }
                )

            except Exception as exc:
                self._log(
                    f"[UnknownSpritesheetHandler] Error detecting background colors for {filename}: {exc}"
                )
                detection_results.append(
                    {"filename": filename, "colors": [], "has_transparency": False}
                )
        return detection_results
