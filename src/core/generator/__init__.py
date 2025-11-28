"""Generator subpackage for creating texture atlases and Starling/Sparrow XML manifests.

Exports:
    AtlasSettings: Dataclass controlling atlas size, padding, and packing heuristics.
    SparrowAtlasGenerator: Packs frames into an atlas and emits a Sparrow XML file.
"""

from .generator import AtlasSettings, SparrowAtlasGenerator

__all__ = ["AtlasSettings", "SparrowAtlasGenerator"]
