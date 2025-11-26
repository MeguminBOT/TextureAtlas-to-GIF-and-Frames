import numpy as np

from core.extractor.image_utils import ensure_rgba_array


class FrameSelector:
    """
    Provides static methods to determine and select frames from a sequence of image tuples,
    supporting various selection strategies and user settings.

    Methods:
        is_single_frame(image_tuples):
            Checks if all frames in the provided image_tuples share the same frame and subframe indices,
            indicating a single unique frame.

        get_kept_frames(settings, single_frame, image_tuples):
            Returns a list of frame indices (as strings) to keep, based on the provided settings and whether
            the sequence is a single frame. Supports options like 'All', 'First', 'Last', 'First, Last',
            'No duplicates', or a comma-separated list of indices.

        get_kept_frame_indices(kept_frames, image_tuples):
            Converts a list of kept frame specifiers (indices, ranges, or keywords) into a sorted list of
            unique integer indices, handling negative indices and range notations.
    """

    @staticmethod
    def is_single_frame(image_tuples):
        """Return True only when all rendered frames are identical."""
        if not image_tuples or len(image_tuples) == 1:
            return True

        _, first_image, first_meta = image_tuples[0]
        first_array = ensure_rgba_array(first_image)

        try:
            first_bytes = first_array.tobytes()
        except Exception:
            first_bytes = None

        first_shape = first_array.shape

        for _, image, metadata in image_tuples[1:]:
            if metadata != first_meta:
                return False

            candidate = ensure_rgba_array(image)
            if candidate.shape != first_shape:
                return False

            if first_bytes is not None:
                try:
                    if candidate.tobytes() != first_bytes:
                        return False
                    continue
                except Exception:
                    first_bytes = None

            if not np.array_equal(candidate, first_array):
                return False

        return True

    @staticmethod
    def get_kept_frames(settings, single_frame, image_tuples):
        if single_frame:
            return ["0"]

        kept_frames = settings.get("frame_selection")
        if kept_frames is None:
            kept_frames = "All"

        if kept_frames == "All":
            return [str(i) for i in range(len(image_tuples))]
        elif kept_frames == "First":
            return ["0"]
        elif kept_frames == "Last":
            return ["-1"]
        elif kept_frames == "First, Last":
            return ["0", "-1"]
        elif kept_frames == "No duplicates":
            unique_indices = []
            seen_signatures = set()
            for i, frame in enumerate(image_tuples):
                signature = FrameSelector._frame_signature(frame[1])
                if signature is None or signature not in seen_signatures:
                    if signature is not None:
                        seen_signatures.add(signature)
                    unique_indices.append(str(i))
            return unique_indices
        else:
            return kept_frames.split(",")

    @staticmethod
    def get_kept_frame_indices(kept_frames, image_tuples):
        kept_frame_indices = set()

        if isinstance(kept_frames, str):
            kept_frames = kept_frames.split(",")

        for entry in kept_frames:
            entry = entry.strip()

            if "--" in entry:  # Detect ranges like "-1--4"
                try:
                    split_index = entry[1:].find("-") + 1
                    start = int(entry[:split_index])
                    end = int(entry[split_index + 1 :])

                    if start < 0:
                        start += len(image_tuples)
                    if end < 0:
                        end += len(image_tuples)

                    if start <= end:
                        kept_frame_indices.update(
                            range(max(0, start), min(len(image_tuples), end + 1))
                        )
                    else:
                        kept_frame_indices.update(
                            range(max(0, end), min(len(image_tuples), start + 1))[::-1]
                        )
                except ValueError:
                    continue

            elif (
                "-" in entry and not entry.lstrip("-").isdigit()
            ):  # Detect ranges like "0-3"
                try:
                    start, end = map(int, entry.split("-"))
                    if start < 0:
                        start += len(image_tuples)
                    if end < 0:
                        end += len(image_tuples)

                    if start <= end:
                        kept_frame_indices.update(
                            range(max(0, start), min(len(image_tuples), end + 1))
                        )
                    else:
                        kept_frame_indices.update(
                            range(max(0, end), min(len(image_tuples), start + 1))[::-1]
                        )
                except ValueError:
                    continue

            else:
                try:
                    frame_index = int(entry)
                    if frame_index < 0:
                        frame_index += len(image_tuples)
                    if 0 <= frame_index < len(image_tuples):
                        kept_frame_indices.add(frame_index)
                except ValueError:
                    continue
        return sorted(kept_frame_indices)

    @staticmethod
    def _frame_signature(frame_source):
        try:
            array = ensure_rgba_array(frame_source)
        except Exception:
            return None

        if array.ndim < 2:
            return None

        step_y = max(1, array.shape[0] // 32)
        step_x = max(1, array.shape[1] // 32)
        sample = array[::step_y, ::step_x]
        if sample.ndim == 3 and sample.shape[2] > 4:
            sample = sample[..., :4]

        try:
            sample = np.ascontiguousarray(sample)
            prefix = sample.tobytes()
        except Exception:
            return None

        return hash((array.shape, array.dtype.str, prefix))
