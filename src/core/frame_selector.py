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

        try:
            first_bytes = first_image.tobytes()
        except Exception:
            first_bytes = None

        for _, image, metadata in image_tuples[1:]:
            if metadata != first_meta:
                return False

            if first_bytes is not None:
                try:
                    if image.tobytes() != first_bytes:
                        return False
                    continue
                except Exception:
                    first_bytes = None

            if image.size != first_image.size:
                return False

            try:
                from PIL import ImageChops

                if ImageChops.difference(image, first_image).getbbox():
                    return False
            except Exception:
                if image is not first_image:
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
            unique_frames = []
            unique_indices = []
            for i, frame in enumerate(image_tuples):
                if frame[1] not in unique_frames:
                    unique_frames.append(frame[1])
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

            elif "-" in entry and not entry.lstrip("-").isdigit():  # Detect ranges like "0-3"
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
