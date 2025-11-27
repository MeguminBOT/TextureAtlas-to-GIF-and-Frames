"""Extractor subpackage for parsing spritesheets and exporting animations.

This package provides the multi-threaded extraction pipeline that parses
various atlas formats, extracts individual frames, and exports animations
as GIF, APNG, or WebP files.

Exports:
    Extractor: Orchestrates parallel spritesheet processing with worker threads.
    ExtractionCancelled: Raised when a batch run is aborted by the user.
    FileProcessorWorker: QThread subclass that processes files from a queue.
    AnimationProcessor: Sequences frames and delegates to animation exporters.
    AtlasProcessor: Loads atlas images and parses associated metadata.
    FrameSelector: Filters frames by animation name or user selection.
    FrameExporter: Writes individual frame images to disk.
    AnimationExporter: Renders GIF, APNG, or WebP from frame sequences.
    PreviewGenerator: Creates temporary animation files for UI preview.
    SpriteProcessor: Groups parsed sprites into animation buckets.
    UnknownSpritesheetHandler: Fallback for atlas images lacking metadata.
"""

from .extractor import Extractor, FileProcessorWorker, ExtractionCancelled
from .animation_processor import AnimationProcessor
from .atlas_processor import AtlasProcessor
from .frame_selector import FrameSelector
from .frame_exporter import FrameExporter
from .animation_exporter import AnimationExporter
from .preview_generator import PreviewGenerator
from .sprite_processor import SpriteProcessor
from .unknown_spritesheet_handler import UnknownSpritesheetHandler

__all__ = [
    "Extractor",
    "ExtractionCancelled",
    "FileProcessorWorker",
    "AnimationProcessor",
    "AtlasProcessor",
    "FrameSelector",
    "FrameExporter",
    "AnimationExporter",
    "PreviewGenerator",
    "SpriteProcessor",
    "UnknownSpritesheetHandler",
]
