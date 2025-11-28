"""Generator subpackage for creating texture atlases and Starling/Sparrow XML manifests.

Exports:
    AtlasSettings: Dataclass controlling atlas size, padding, and packing heuristics.
    SparrowAtlasGenerator: Packs frames into an atlas and emits a Sparrow XML file.
    MetadataWriter: Writes atlas metadata in various formats.
"""

from .generator import AtlasSettings, SparrowAtlasGenerator
from .metadata_writer import MetadataWriter

__all__ = ["AtlasSettings", "SparrowAtlasGenerator", "MetadataWriter"]
