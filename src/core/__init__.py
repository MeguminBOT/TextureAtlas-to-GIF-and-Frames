"""Core package collecting the logic for extraction, editing, and atlas generation.

Subpackages:
    editor: Builds composite animations from existing frame sources.
    extractor: Parses spritesheets, extracts frames, and exports animations.
    generator: Creates texture atlases and associated Sparrow XML manifests.

Modules:
    exception_handler: Maps low-level errors to user-friendly dialog messages.

This module re-exports the extractor classes most callers need; import
editor or generator tooling directly from their subpackages when required.
"""

from core.extractor import (
    AnimationExporter,
    AnimationProcessor,
    AtlasProcessor,
    Extractor,
    FileProcessorWorker,
    FrameExporter,
    FrameSelector,
    PreviewGenerator,
    SpriteProcessor,
    UnknownSpritesheetHandler,
)

__all__ = [
    "AnimationExporter",
    "AnimationProcessor",
    "AtlasProcessor",
    "Extractor",
    "FileProcessorWorker",
    "FrameExporter",
    "FrameSelector",
    "PreviewGenerator",
    "SpriteProcessor",
    "UnknownSpritesheetHandler",
]
