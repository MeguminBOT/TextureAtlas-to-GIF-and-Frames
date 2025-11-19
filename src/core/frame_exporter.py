import os
from PIL.PngImagePlugin import PngInfo
import pillow_avif # DO NOT REMOVE

# Import our own modules
from utils.utilities import Utilities


class FrameExporter:
    """
    Exports individual frames from a spritesheet as images.

    Attributes:
        output_dir (str):
            Directory where exported frames will be saved.
        current_version (str):
            Version string to include in metadata.
        scale_image_func (callable):
            Function to scale images before saving.

    Methods:
        save_frames(image_tuples, kept_frame_indices, spritesheet_name, animation_name, scale, settings, is_unknown_spritesheet=False) -> int
            Saves selected frames, applying cropping and scaling as specified in settings.
            The is_unknown_spritesheet parameter determines whether to apply extra cropping.
            Returns the number of frames successfully exported.
        _save_frame_to_image(image, filename, frame_format)
            Saves the frames in the specified format.
        _apply_extra_crop_pass(image)
            Applies extra cropping to remove excessive whitespace around the sprite.
    """

    def __init__(self, output_dir, current_version, scale_image_func):
        self.output_dir = output_dir
        self.current_version = current_version
        self.scale_image = scale_image_func

    def save_frames(self, image_tuples, kept_frame_indices, spritesheet_name, animation_name, scale, settings, is_unknown_spritesheet=False):
        frames_generated = 0
        if len(image_tuples) == 0:
            return frames_generated

        frame_format = settings.get("frame_format", "PNG")
        frame_scale = settings.get("frame_scale", scale)

        safe_animation_folder = Utilities.replace_invalid_chars(animation_name)
        frames_folder = os.path.join(self.output_dir, safe_animation_folder)
        os.makedirs(frames_folder, exist_ok=True)

        crop_option = settings.get("crop_option")

        format_extensions = {
            "AVIF": ".avif",
            "BMP": ".bmp",
            "DDS": ".dds",
            "PNG": ".png",
            "TGA": ".tga",
            "TIFF": ".tiff",
            "WebP": ".webp",
        }
        file_extension = format_extensions.get(frame_format, ".png")

        if crop_option == "Animation based":
            min_x, min_y, max_x, max_y = float("inf"), float("inf"), 0, 0
            for index, frame in enumerate(image_tuples):
                if index in kept_frame_indices:
                    bbox = frame[1].getbbox()
                    if bbox:
                        min_x = min(min_x, bbox[0])
                        min_y = min(min_y, bbox[1])
                        max_x = max(max_x, bbox[2])
                        max_y = max(max_y, bbox[3])

            if min_x > max_x:
                return frames_generated

        for index, frame in enumerate(image_tuples):
            if index in kept_frame_indices:
                formatted_frame_name = Utilities.format_filename(
                    settings.get("prefix"),
                    spritesheet_name,
                    frame[0],
                    settings.get("filename_format"),
                    settings.get("replace_rules"),
                    settings.get("suffix"),
                )

                frame_filename = os.path.join(
                    frames_folder, f"{formatted_frame_name}{file_extension}"
                )
                frame_image = frame[1]

                bbox = frame_image.getbbox()
                if bbox:
                    if crop_option == "Frame based":
                        cropped_frame = frame_image.crop(bbox)
                        if is_unknown_spritesheet:
                            extra_cropped_frame = self._apply_extra_crop_pass(cropped_frame)
                            final_frame_image = self.scale_image(
                                extra_cropped_frame, frame_scale
                            )
                        else:
                            final_frame_image = self.scale_image(
                                cropped_frame, frame_scale
                            )

                    elif crop_option == "Animation based":
                        cropped_frame = frame_image.crop((min_x, min_y, max_x, max_y))
                        if is_unknown_spritesheet:
                            extra_cropped_frame = self._apply_extra_crop_pass(cropped_frame)
                            final_frame_image = self.scale_image(
                                extra_cropped_frame, frame_scale
                            )
                        else:
                            final_frame_image = self.scale_image(
                                cropped_frame, frame_scale
                            )

                    else:
                        if is_unknown_spritesheet:
                            extra_cropped_frame = self._apply_extra_crop_pass(frame_image)
                            final_frame_image = self.scale_image(
                                extra_cropped_frame, frame_scale
                            )
                        else:
                            final_frame_image = self.scale_image(
                                frame_image, frame_scale
                            )

                    self._save_frame_to_image(
                        final_frame_image,
                        frame_filename,
                        frame_format,
                        settings.get("compression_settings"),
                    )
                    frames_generated += 1
                    print(f"Saved frame: {frame_filename}")
        return frames_generated

    def _save_frame_to_image(self, image, filename, frame_format, compression_settings=None):
        save_kwargs = {}

        if compression_settings is None:
            compression_settings = {}

        if frame_format == "AVIF":
            save_kwargs["format"] = "AVIF"
            save_kwargs["lossless"] = compression_settings.get("avif_lossless", True)
            save_kwargs["quality"] = compression_settings.get("avif_quality", 100)
            save_kwargs["speed"] = compression_settings.get("avif_speed", 0)

        elif frame_format == "BMP":
            save_kwargs["format"] = "BMP"

        elif frame_format == "DDS":
            save_kwargs["format"] = "DDS"

        elif frame_format == "PNG":
            metadata = PngInfo()
            metadata.add_text(
                "Comment",
                f"PNG generated by TextureAtlas to GIF and Frames v{self.current_version}",
            )
            save_kwargs["pnginfo"] = metadata
            save_kwargs["format"] = "PNG"
            save_kwargs["compress_level"] = compression_settings.get(
                "png_compress_level", 9
            )
            save_kwargs["optimize"] = compression_settings.get("png_optimize", True)

        elif frame_format == "TGA":
            save_kwargs["format"] = "TGA"
            save_kwargs["compression"] = compression_settings.get(
                "tga_compression", "tga_rle"
            )

        elif frame_format == "TIFF":
            save_kwargs["format"] = "TIFF"

            compression_type = compression_settings.get("tiff_compression_type", "lzw")
            save_kwargs["compression"] = (
                compression_type if compression_type != "none" else None
            )

            if compression_type == "jpeg":
                save_kwargs["quality"] = compression_settings.get("tiff_quality", 90)

            save_kwargs["optimize"] = compression_settings.get("tiff_optimize", True)

            if hasattr(image, "info"):
                image.info["description"] = (
                    f"TIFF generated by TextureAtlas to GIF and Frames v{self.current_version}"
                )

        elif frame_format == "WebP":
            save_kwargs["format"] = "WebP"

            save_kwargs["lossless"] = compression_settings.get("webp_lossless", True)
            if not save_kwargs["lossless"]:
                save_kwargs["quality"] = compression_settings.get("webp_quality", 100)
            save_kwargs["method"] = compression_settings.get("webp_method", 6)
            save_kwargs["alpha_quality"] = compression_settings.get("webp_alpha_quality", 100)
            save_kwargs["exact"] = compression_settings.get("webp_exact", True)

        try:
            image.save(filename, **save_kwargs)
            print(f"Successfully saved {filename} as {frame_format}")

        except Exception as e:
            print(f"Error saving {filename} as {frame_format}: {e}")
            try:
                png_filename = filename.rsplit(".", 1)[0] + ".png"
                metadata = PngInfo()
                metadata.add_text(
                    "Comment",
                    f"PNG generated by TextureAtlas to GIF and Frames v{self.current_version}",
                )
                image.save(
                    png_filename,
                    format="PNG",
                    pnginfo=metadata,
                    compress_level=9,
                    optimize=True,
                )
                print(f"Fallback: Successfully saved {png_filename} as PNG")
            except Exception as fallback_e:
                print(f"Critical error: Could not save image even as PNG: {fallback_e}")

    def _apply_extra_crop_pass(self, image):
        try:
            bbox = image.getbbox()
            if bbox:
                padding = 2
                left, top, right, bottom = bbox
                width, height = image.size

                left = max(0, left - padding)
                top = max(0, top - padding)
                right = min(width, right + padding)
                bottom = min(height, bottom + padding)

                # Only crop if it would actually reduce the canvas size significantly
                # (avoid cropping if the reduction is minimal)
                new_width = right - left
                new_height = bottom - top
                original_area = width * height
                new_area = new_width * new_height

                if new_area < original_area * 0.75:
                    return image.crop((left, top, right, bottom))

            return image
        except Exception as e:
            print(f"Warning: Extra crop failed, using original image: {e}")
            return image
