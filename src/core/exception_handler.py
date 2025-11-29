"""Helpers for raising user-friendly error dialogs during extraction.

Provides utilities for mapping low-level parsing errors to readable messages
and integrates with the unified parser error system.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from parsers.parser_types import (
    ParserError,
    ParserErrorCode,
    ParseResult,
)


class ExceptionHandler:
    """Utility namespace for mapping low-level errors to readable messages."""

    # Map error codes to user-friendly message templates
    ERROR_MESSAGES = {
        ParserErrorCode.FILE_NOT_FOUND: "The metadata file was not found.\n\nFile: {file_path}",
        ParserErrorCode.FILE_READ_ERROR: "Could not read the metadata file.\n\nError: {message}\n\nFile: {file_path}",
        ParserErrorCode.FILE_ENCODING_ERROR: "The metadata file has encoding issues.\n\nError: {message}\n\nFile: {file_path}",
        ParserErrorCode.INVALID_FORMAT: "The metadata file format is invalid.\n\nError: {message}\n\nFile: {file_path}",
        ParserErrorCode.UNSUPPORTED_FORMAT: "This metadata format is not supported.\n\nFile: {file_path}",
        ParserErrorCode.MALFORMED_STRUCTURE: "The metadata file structure is malformed.\n\nError: {message}\n\nFile: {file_path}",
        ParserErrorCode.MISSING_REQUIRED_KEY: "A required key is missing from the metadata.\n\nError: {message}\n\nFile: {file_path}",
        ParserErrorCode.INVALID_VALUE_TYPE: "A value in the metadata has an incorrect type.\n\nError: {message}\n\nFile: {file_path}",
        ParserErrorCode.INVALID_COORDINATE: "Invalid coordinate values in metadata.\n\nError: {message}\n\nFile: {file_path}\n\nThis error can also occur from Alpha Threshold being set too high.",
        ParserErrorCode.NEGATIVE_DIMENSION: "Sprite has negative dimensions.\n\nError: {message}\n\nFile: {file_path}",
        ParserErrorCode.ZERO_DIMENSION: "Sprite has zero dimensions.\n\nError: {message}\n\nFile: {file_path}",
        ParserErrorCode.SPRITE_PARSE_FAILED: "Failed to parse sprite data.\n\nError: {message}\n\nFile: {file_path}",
        ParserErrorCode.SPRITE_OUT_OF_BOUNDS: "Sprite coordinates extend beyond atlas bounds.\n\nError: {message}\n\nFile: {file_path}\n\nThis error can also occur from Alpha Threshold being set too high.",
        ParserErrorCode.DUPLICATE_SPRITE_NAME: "Duplicate sprite names found in metadata.\n\nWarning: {message}\n\nFile: {file_path}",
        ParserErrorCode.MISSING_FRAMES_KEY: "The metadata file is missing the 'frames' section.\n\nFile: {file_path}",
        ParserErrorCode.MISSING_TEXTURES_KEY: "The metadata file is missing the 'textures' section.\n\nFile: {file_path}",
        ParserErrorCode.EMPTY_SPRITE_LIST: "No valid sprites found in metadata.\n\nFile: {file_path}",
        ParserErrorCode.UNKNOWN_ERROR: "An unexpected error occurred.\n\nError: {message}\n\nFile: {file_path}",
    }

    @staticmethod
    def handle_exception(
        e: Exception,
        metadata_path: str,
        sprites_failed: int,
    ) -> Tuple[int, Exception]:
        """Convert an exception to a user-friendly error message.

        Args:
            e: The exception that was raised.
            metadata_path: Path to the metadata file.
            sprites_failed: Current count of failed sprites.

        Returns:
            Tuple of (updated sprites_failed count, new Exception with user message).
        """
        sprites_failed += 1

        # Handle new ParserError types
        if isinstance(e, ParserError):
            message = ExceptionHandler.format_parser_error(e, metadata_path)
            return sprites_failed, Exception(message)

        # Legacy string-based error detection
        error_str = str(e)

        if "Coordinate '" in error_str and "' is less than '" in error_str:
            message = (
                f"XML or TXT frame dimension data doesn't match the spritesheet dimensions.\n\n"
                f"Error: {error_str}\n\n"
                f"File: {metadata_path}\n\n"
                f"This error can also occur from Alpha Threshold being set too high."
            )
        elif "'NoneType' object is not subscriptable" in error_str:
            message = (
                f"XML or TXT frame dimension data doesn't match the spritesheet dimensions.\n\n"
                f"Error: {error_str}\n\n"
                f"File: {metadata_path}"
            )
        else:
            message = f"An error occurred: {error_str}.\n\nFile: {metadata_path}"

        return sprites_failed, Exception(message)

    @staticmethod
    def format_parser_error(
        error: ParserError,
        fallback_path: Optional[str] = None,
    ) -> str:
        """Format a ParserError into a user-friendly message.

        Args:
            error: The ParserError to format.
            fallback_path: Path to use if error.file_path is None.

        Returns:
            Formatted error message string.
        """
        file_path = error.file_path or fallback_path or "Unknown file"
        template = ExceptionHandler.ERROR_MESSAGES.get(
            error.code,
            ExceptionHandler.ERROR_MESSAGES[ParserErrorCode.UNKNOWN_ERROR],
        )

        return template.format(
            message=error.message,
            file_path=file_path,
        )

    @staticmethod
    def format_parse_result(
        result: ParseResult,
        include_warnings: bool = True,
    ) -> str:
        """Format a ParseResult into a summary message.

        Args:
            result: The ParseResult to format.
            include_warnings: Whether to include warnings in output.

        Returns:
            Formatted summary string.
        """
        lines = []

        if result.is_valid:
            lines.append(f"Successfully parsed {result.sprite_count} sprites.")
        else:
            lines.append("Failed to parse sprites.")

        if result.errors:
            lines.append(f"\nErrors ({result.error_count}):")
            for error in result.errors[:5]:  # Limit to first 5
                lines.append(f"  - {error.message}")
            if result.error_count > 5:
                lines.append(f"  ... and {result.error_count - 5} more errors")

        if include_warnings and result.warnings:
            lines.append(f"\nWarnings ({result.warning_count}):")
            for warning in result.warnings[:5]:
                lines.append(f"  - {warning.message}")
            if result.warning_count > 5:
                lines.append(f"  ... and {result.warning_count - 5} more warnings")

        if result.file_path:
            lines.append(f"\nFile: {result.file_path}")

        return "\n".join(lines)

    @staticmethod
    def handle_validation_error(key: str, expected_type: Any) -> str:
        """Return a readable validation error message for settings entries.

        Args:
            key: The settings key that failed validation.
            expected_type: The expected type or callable.

        Returns:
            Human-readable error message.
        """
        if hasattr(expected_type, "__name__"):
            readable_type = expected_type.__name__
            if readable_type == "<lambda>":
                readable_type = "number"
        else:
            readable_type = "number"
        return f"'{key}' must be a valid {readable_type}."

    @staticmethod
    def should_show_error_dialog(result: ParseResult) -> bool:
        """Determine if a ParseResult warrants showing an error dialog.

        Args:
            result: The ParseResult to check.

        Returns:
            True if an error dialog should be shown.
        """
        # Show dialog if parsing completely failed
        if not result.is_valid:
            return True

        # Show dialog if there are critical errors
        critical_codes = {
            ParserErrorCode.FILE_NOT_FOUND,
            ParserErrorCode.INVALID_FORMAT,
            ParserErrorCode.UNSUPPORTED_FORMAT,
        }
        for error in result.errors:
            if error.code in critical_codes:
                return True

        return False

    @staticmethod
    def should_prompt_removal(result: ParseResult) -> bool:
        """Determine if user should be prompted to remove file from extraction list.

        Args:
            result: The ParseResult to check.

        Returns:
            True if user should be asked about removing the file.
        """
        # Prompt for removal if file cannot be parsed at all
        if not result.is_valid:
            return True

        # Prompt if more than half of sprites failed
        if result.error_count > result.sprite_count:
            return True

        return False


__all__ = ["ExceptionHandler"]
