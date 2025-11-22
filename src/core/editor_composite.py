"""Helpers for building editor-defined composite animations."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

FrameTuple = Tuple[str, Any, dict]
AnimationMap = Dict[str, List[FrameTuple]]


def clone_animation_map(animations: Optional[Dict[str, Sequence[FrameTuple]]]) -> AnimationMap:
    """Create a deep-ish copy of an animation map without duplicating images."""
    cloned: AnimationMap = {}
    if not animations:
        return cloned
    for name, frames in animations.items():
        cloned[name] = list(frames or [])
    return cloned


def build_editor_composite_frames(
    definition: Optional[dict],
    source_frames: AnimationMap,
    *,
    log_warning: Optional[Callable[[str], None]] = None,
) -> List[FrameTuple]:
    """Construct a list of frames for an editor composite definition."""

    def warn(message: str):
        if log_warning:
            try:
                log_warning(message)
            except Exception:
                print(message)
        else:
            print(message)

    if not isinstance(definition, dict):
        return []
    sequence = definition.get("sequence")
    if not isinstance(sequence, list):
        return []

    frames: List[FrameTuple] = []
    composite_name = definition.get("name") or "editor_composite"

    for index, frame_spec in enumerate(sequence):
        source_frame = _fetch_source_frame(frame_spec, source_frames)
        if source_frame is None:
            warn(
                f"[EditorComposite] Skipping composite '{composite_name}' because a referenced frame could not be resolved."
            )
            return []

        original_name, image, metadata = source_frame
        original_key = frame_spec.get("original_key") or original_name
        frame_name = original_key or frame_spec.get("name") or original_name or f"frame_{index}"

        frame_metadata = _coerce_metadata(metadata)
        if "duration_ms" in frame_spec:
            frame_metadata["duration_ms"] = frame_spec.get("duration_ms")
        frame_metadata.setdefault("original_key", original_key or frame_name)
        frame_metadata["editor_source_animation"] = frame_spec.get("source_animation")
        frame_metadata["editor_source_frame_index"] = frame_spec.get("source_frame_index")
        frame_metadata["editor_sequence_index"] = index

        frame_image = image.copy() if hasattr(image, "copy") else image
        frames.append((frame_name, frame_image, frame_metadata))

    return frames


def _coerce_metadata(metadata: Any) -> dict:
    if isinstance(metadata, dict):
        return dict(metadata)
    if metadata is None:
        return {}
    if isinstance(metadata, (list, tuple)):
        return {"original_sprite_bounds": tuple(metadata)}
    return {"metadata": metadata}


def _fetch_source_frame(frame_spec: Optional[dict], source_frames: AnimationMap):
    if not isinstance(frame_spec, dict):
        return None
    source_animation = frame_spec.get("source_animation")
    source_index = frame_spec.get("source_frame_index")
    if source_animation is None or source_index is None:
        return None

    try:
        source_index = int(source_index)
    except (TypeError, ValueError):
        return None

    frames = source_frames.get(source_animation)
    if not frames or source_index < 0 or source_index >= len(frames):
        return None

    original_key = frame_spec.get("original_key")
    candidate = frames[source_index]
    if original_key and candidate and candidate[0] != original_key:
        for tuple_candidate in frames:
            if tuple_candidate and tuple_candidate[0] == original_key:
                return tuple_candidate
    return candidate
