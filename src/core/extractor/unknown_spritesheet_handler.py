"""Background color detection for spritesheets without metadata.

Provides ``UnknownSpritesheetHandler`` which identifies images lacking XML/TXT
metadata, detects their background colors, and prompts the user to choose
how to handle them before extraction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Sequence

from PIL import Image

from gui.extractor.background_handler_window import BackgroundHandlerWindow
from parsers.unknown_parser import UnknownParser


class UnknownSpritesheetHandler:
    """Detect and handle background colors for spritesheets without metadata.

    Identifies images missing XML, TXT, or spritemap JSON files, analyses them
    for transparency and background colors, and shows a dialog for user input.

    Attributes:
        SUPPORTED_IMAGE_SUFFIXES: Tuple of file extensions considered valid.
    """

    SUPPORTED_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")

    def __init__(self, logger: Callable[[str], None] | None = None):
        """Initialise the handler with an optional logger.

        Args:
            logger: Callable for status messages; defaults to ``print``.
        """
        self._log = logger or print

    def handle_background_detection(
        self,
        input_dir: str,
        spritesheet_list: Sequence[str],
        parent_window,
    ) -> bool:
        """Run the background detection workflow for unknown spritesheets.

        Scans for images lacking metadata, detects background colors, and
        displays a dialog if user input is required.

        Args:
            input_dir: Root directory containing the images.
            spritesheet_list: Relative filenames to check.
            parent_window: Parent widget for the dialog.

        Returns:
            ``True`` if the user cancelled extraction, ``False`` otherwise.
        """
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
        """Identify spritesheets that lack accompanying metadata files.

        Args:
            base_directory: Root path for resolving relative filenames.
            spritesheet_list: Relative filenames to check.

        Returns:
            List of filenames with no XML, TXT, or spritemap JSON metadata.
        """
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
        """Analyse unknown spritesheets for transparency and background colors.

        Args:
            base_directory: Root path for resolving relative filenames.
            unknown_sheets: Filenames previously identified as lacking metadata.

        Returns:
            List of dicts with ``filename``, ``colors``, and ``has_transparency``.
        """
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
