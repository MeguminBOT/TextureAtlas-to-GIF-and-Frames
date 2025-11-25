import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from queue import SimpleQueue, Empty
from threading import Event

from PySide6.QtCore import QCoreApplication, QThread, Signal

# Import our own modules
from core.extractor.atlas_processor import AtlasProcessor
from core.extractor.sprite_processor import SpriteProcessor
from core.extractor.animation_processor import AnimationProcessor
from core.extractor.preview_generator import PreviewGenerator
from core.extractor.spritemap import AdobeSpritemapRenderer
from core.extractor.unknown_spritesheet_handler import UnknownSpritesheetHandler
from utils.utilities import Utilities


class Extractor:
    """
    A class to extract sprites from a directory of spritesheets and their corresponding metadata files.

    Attributes:
        progress_callback (callable): Callback function to update progress during processing.
        current_version (str): The current version of the extractor.
        settings_manager (SettingsManager): Manages global, animation-specific, and spritesheet-specific settings.
        app_config (AppConfig): Configuration for resource limits (CPU/memory).
        fnf_idle_loop (bool): A flag to determine if idle animations should have a loop delay of 0.

    Methods:
        process_directory(input_dir, output_dir, progress_callback, parent_window=None, spritesheet_list=None):
            Processes the given directory of spritesheets and metadata files, extracting sprites and generating animations.
            Returns early without processing if the user cancels background color detection dialogs.
        extract_sprites(atlas_path, metadata_path, output_dir, settings):
            Extracts sprites from a given atlas and metadata file, and processes the animations.
        generate_temp_animation_for_preview(atlas_path, metadata_path, settings, animation_name, temp_dir=None):
            Generates a temporary animated image file for preview purposes using optimized processing
            that only loads sprites belonging to the specific animation.
    """

    def __init__(
        self,
        progress_callback,
        current_version,
        settings_manager,
        app_config=None,
        statistics_callback=None,
    ):
        self.settings_manager = settings_manager
        self.progress_callback = progress_callback
        self.statistics_callback = statistics_callback
        self.current_version = current_version
        self.app_config = app_config
        self.fnf_idle_loop = False
        self.preview_generator = PreviewGenerator(settings_manager, current_version)
        self.unknown_handler = UnknownSpritesheetHandler()
        # Opt-in flag so stats logging does not spam unless explicitly requested.
        self._trace_stats = False
        self._stats_queue = SimpleQueue()
        self._progress_callback = None
        self.work_in_progress = {}
        self._worker_labels = {}
        self._last_started_file = None
        self._progress_dirty = False
        self._last_progress_emit = 0.0
        self._progress_emit_interval = 0.12  # seconds between UI payloads
        self._qt_event_interval = 0.04
        self._last_qt_event_pump = 0.0

    def process_directory(
        self,
        input_dir,
        output_dir,
        progress_callback=None,
        parent_window=None,
        spritesheet_list=None,
    ):
        """Process supplied spritesheets using worker threads."""

        self._initialize_processing_state()
        total_files = Utilities.count_spritesheets(spritesheet_list)
        self._progress_callback = self._choose_progress_callback(progress_callback)
        if self._progress_callback:
            self._progress_callback(0, total_files, "Initializing...")

        cpu_threads = self._resolve_cpu_threads()
        filenames = list(spritesheet_list or [])
        self.total_files = len(filenames)
        self.work_in_progress.clear()
        for filename in filenames:
            self.file_queue.put(filename)
        # Push sentinel entries so workers know when to stop.
        # These will only be consumed once all real work is done because they are enqueued last.
        # Using None avoids extra allocations and still keeps intent clear.
        self.start_time = time.time()

        max_threads = self._determine_worker_budget(cpu_threads, len(filenames))
        if max_threads:
            for _ in range(max_threads):
                self.file_queue.put(None)
        else:
            self._workers_done_event.set()
        self._start_worker_pool(
            max_threads,
            input_dir,
            output_dir,
            parent_window,
        )
        self._monitor_workers()
        self._finalize_directory_processing()

        if self.statistics_callback:
            self.statistics_callback(
                self.total_frames_generated,
                self.total_anims_generated,
                self.total_sprites_failed,
            )

    def _initialize_processing_state(self):
        self.total_frames_generated = 0
        self.total_anims_generated = 0
        self.total_sprites_failed = 0
        self.processed_count = 0
        self.active_workers = []
        self._stats_queue = SimpleQueue()
        self.file_queue = SimpleQueue()
        self.work_in_progress = {}
        self._worker_labels = {}
        self._last_started_file = None
        if hasattr(self, "_workers_done_event"):
            self._workers_done_event.clear()
        else:
            self._workers_done_event = Event()
        if hasattr(self, "_stats_available_event"):
            self._stats_available_event.clear()
        else:
            self._stats_available_event = Event()
        self._progress_dirty = False
        self._last_progress_emit = 0.0
        self._last_qt_event_pump = 0.0

    def _choose_progress_callback(self, override_callback):
        return self.progress_callback or override_callback

    def _resolve_cpu_threads(self):
        cpu_threads = max(1, os.cpu_count() // 2)
        if not self.app_config:
            return cpu_threads

        try:
            resource_limits = self.app_config.settings.get("resource_limits", {})
            cpu_cores_val = resource_limits.get("cpu_cores", "auto")

            if cpu_cores_val != "auto":
                configured_threads = int(cpu_cores_val)
                cpu_threads = max(1, min(configured_threads, os.cpu_count()))
            else:
                cpu_threads = max(1, os.cpu_count() // 2)
        except (ValueError, TypeError, KeyError):
            cpu_threads = max(1, os.cpu_count() // 2)
        return cpu_threads

    @staticmethod
    def _determine_worker_budget(cpu_threads, file_count):
        return min(cpu_threads, file_count)

    def _start_worker_pool(
        self,
        max_threads,
        input_dir,
        output_dir,
        parent_window,
    ):
        if not max_threads:
            return

        for i in range(max_threads):
            worker = FileProcessorWorker(
                input_dir,
                output_dir,
                parent_window,
                self,
                self.file_queue,
            )

            label = f"Worker {i + 1}"
            worker.setObjectName(label)
            self._worker_labels[worker] = label

            worker.file_completed.connect(self._on_file_completed)
            worker.file_failed.connect(self._on_file_failed)
            worker.task_started.connect(
                lambda filename, w=worker: self._on_worker_task_started(w, filename)
            )
            worker.task_finished.connect(
                lambda filename, w=worker: self._on_worker_task_finished(w, filename)
            )
            worker.finished.connect(lambda w=worker: self._worker_finished(w))

            self.active_workers.append(worker)
            worker.start()

    def _monitor_workers(self):
        """Drain statistics queue using blocking waits to reduce idle spin."""
        while True:
            processed = self._drain_stats_queue()
            if not processed:
                timeout = self._compute_wait_timeout()
                woke_for_stats = self._stats_available_event.wait(timeout)
                if not woke_for_stats:
                    self._maybe_process_qt_events(force=True)
                else:
                    self._maybe_process_qt_events()
            else:
                self._maybe_process_qt_events()

            self._update_progress_text()

            if self._workers_done_event.is_set() and self._stats_queue_empty():
                break

        self._drain_stats_queue()
        self._update_progress_text(force=True)

    @staticmethod
    def _process_qt_events():
        app = QCoreApplication.instance()
        if app is not None:
            QCoreApplication.processEvents()

    def _maybe_process_qt_events(self, *, force=False):
        now = time.monotonic()
        if force or (now - self._last_qt_event_pump) >= self._qt_event_interval:
            self._process_qt_events()
            self._last_qt_event_pump = now

    def _compute_wait_timeout(self):
        active_tasks = len(self.work_in_progress)
        if active_tasks:
            return 0.015
        if self.active_workers:
            return 0.05
        return 0.08

    def _finalize_directory_processing(self):
        end_time = time.time()
        duration = end_time - self.start_time
        self._last_processing_finished = end_time
        self._last_processing_duration = duration
        self._last_processing_totals = (
            self.total_frames_generated,
            self.total_anims_generated,
            self.total_sprites_failed,
        )

    def _queue_stats_update(
        self,
        *,
        frames_delta=0,
        anims_delta=0,
        failed_delta=0,
        processed_delta=1,
        debug_message=None,
    ):
        update = {
            "frames_delta": frames_delta,
            "anims_delta": anims_delta,
            "failed_delta": failed_delta,
            "processed_delta": processed_delta,
            "debug_message": debug_message,
        }
        self._stats_queue.put(update)
        if hasattr(self, "_stats_available_event"):
            self._stats_available_event.set()

    def _drain_stats_queue(self):
        processed = False
        while True:
            try:
                update = self._stats_queue.get(block=False)
            except Empty:
                break
            self._apply_stats_update(update)
            processed = True

        if processed:
            self._update_progress_text()

        if not self._stats_queue_empty() and hasattr(self, "_stats_available_event"):
            # Leave event set so waiters wake immediately for remaining items.
            pass
        elif hasattr(self, "_stats_available_event"):
            self._stats_available_event.clear()

        return processed

    def _stats_queue_empty(self):
        return self._stats_queue.empty()

    def _apply_stats_update(self, update):
        frames_delta = update.get("frames_delta", 0)
        anims_delta = update.get("anims_delta", 0)
        failed_delta = update.get("failed_delta", 0)

        processed_delta = update.get("processed_delta", 0)

        self.total_frames_generated += frames_delta
        self.total_anims_generated += anims_delta
        self.total_sprites_failed += failed_delta
        self.processed_count += processed_delta

        stats_snapshot = (
            self.total_frames_generated,
            self.total_anims_generated,
            self.total_sprites_failed,
        )

        if self._trace_stats:
            print(
                f"[_apply_stats_update] Totals: {stats_snapshot[0]} frames, {stats_snapshot[1]} anims, {stats_snapshot[2]} failed"
            )

        if self.statistics_callback:
            self.statistics_callback(*stats_snapshot)

        self._progress_dirty = True

    def _on_worker_task_started(self, worker, filename):
        if worker:
            self.work_in_progress[worker] = filename
        if filename:
            self._last_started_file = str(filename)
        self._progress_dirty = True
        self._update_progress_text(force=True)

    def _on_worker_task_finished(self, worker, filename):
        if worker in self.work_in_progress:
            self.work_in_progress.pop(worker, None)
        self._progress_dirty = True
        self._update_progress_text(force=True)

    def _update_progress_text(self, *, force=False):
        if not self._progress_callback:
            return

        if not force and not self._progress_dirty:
            return

        now = time.monotonic()
        if not force and (now - self._last_progress_emit) < self._progress_emit_interval:
            return

        snapshot = self._build_worker_status_snapshot()
        summary_text = snapshot.get("summary") if snapshot else ""
        if summary_text:
            current_files_text = summary_text
        elif self.active_workers:
            current_files_text = "Initializing..."
        else:
            current_files_text = "Completing..."

        total = getattr(self, "total_files", 0)
        if snapshot is not None:
            snapshot["fallback"] = current_files_text
        self._progress_callback(
            self.processed_count, total, snapshot or current_files_text
        )
        self._progress_dirty = False
        self._last_progress_emit = now

    def _build_worker_status_snapshot(self, limit=4):
        worker_rows = []
        processing_count = 0

        for idx, worker in enumerate(self.active_workers):
            label = self._worker_labels.get(worker, f"Worker {idx + 1}")
            current = self.work_in_progress.get(worker)
            display_name = Path(current).name if current else "idle"
            if current:
                processing_count += 1
            worker_rows.append(
                {
                    "label": label,
                    "display": display_name,
                    "path": str(current) if current else "",
                    "state": "processing" if current else "idle",
                }
            )

        worker_count = len(self.active_workers)
        if worker_count:
            summary = self._format_worker_summary(processing_count, worker_count)
        else:
            summary = "No workers active"

        recent_full_path = self._last_started_file
        recent_display = (
            Path(recent_full_path).name if recent_full_path else None
        )

        return {
            "summary": summary,
            "workers": worker_rows,
            "hidden_count": 0,
            "worker_count": worker_count,
            "recent_full_path": recent_full_path,
            "recent_display": recent_display,
        }

    @staticmethod
    def _format_worker_summary(processing_count, worker_count):
        running_plural = "s" if processing_count != 1 else ""
        total_plural = "s" if worker_count != 1 else ""
        return (
            f"{processing_count} worker{running_plural} running "
            f"(of {worker_count} total worker{total_plural})"
        )

    def _on_file_completed(self, filename, result):
        """Handle successful file completion."""
        debug_message = None
        frames_added = 0
        anims_added = 0
        failed_added = 0

        if result:
            frames_added = result.get("frames_generated", 0)
            anims_added = result.get("anims_generated", 0)
            failed_added = result.get("sprites_failed", 0)
        else:
            failed_added = 1

        self._queue_stats_update(
            frames_delta=frames_added,
            anims_delta=anims_added,
            failed_delta=failed_added,
            processed_delta=1,
            debug_message=debug_message,
        )

    def _on_file_failed(self, filename, error):
        """Handle file processing failure."""
        print(f"Error processing {filename}: {error}")

        self._queue_stats_update(failed_delta=1, processed_delta=1)

    def _worker_finished(self, worker):
        """Handle worker shutdown once it has consumed its sentinel."""
        if worker in self.active_workers:
            worker.wait()
            worker.deleteLater()
            self.active_workers.remove(worker)
            self._worker_labels.pop(worker, None)

        self.work_in_progress.pop(worker, None)
        if not self.active_workers:
            self._workers_done_event.set()

        self._progress_dirty = True
        self._update_progress_text(force=True)

    def extract_sprites(
        self,
        atlas_path,
        metadata_path,
        output_dir,
        settings,
        parent_window=None,
        spritesheet_label=None,
    ):
        frames_generated = 0
        anims_generated = 0
        sprites_failed = 0

        try:
            is_unknown_spritesheet = metadata_path is None

            atlas_processor = AtlasProcessor(atlas_path, metadata_path, parent_window)
            sprite_processor = SpriteProcessor(
                atlas_processor.atlas, atlas_processor.sprites
            )
            animations = sprite_processor.process_sprites()
            animation_processor = AnimationProcessor(
                animations,
                atlas_path,
                output_dir,
                self.settings_manager,
                self.current_version,
                spritesheet_label=spritesheet_label,
            )

            frames_generated, anims_generated = animation_processor.process_animations(
                is_unknown_spritesheet
            )
            result = {
                "frames_generated": frames_generated,
                "anims_generated": anims_generated,
                "sprites_failed": sprites_failed,
            }
            return result

        except ET.ParseError:
            sprites_failed += 1
            print(
                f"[extract_sprites] ParseError for {atlas_path}: sprites_failed = {sprites_failed}"
            )
            raise ET.ParseError(f"Badly formatted XML file:\n\n{metadata_path}")

        except Exception as e:
            sprites_failed += 1
            print(
                f"[extract_sprites] Exception for {atlas_path}: {str(e)}, sprites_failed = {sprites_failed}"
            )
            print(
                f"[extract_sprites] Returning error result: frames_generated=0, anims_generated=0, sprites_failed={sprites_failed}"
            )
            # Return a result even on failure so statistics can be updated
            return {
                "frames_generated": 0,
                "anims_generated": 0,
                "sprites_failed": sprites_failed,
            }

    def extract_spritemap_project(
        self,
        atlas_path,
        animation_json_path,
        spritemap_json_path,
        output_dir,
        settings,
        spritesheet_label=None,
    ):
        frames_generated = 0
        anims_generated = 0
        sprites_failed = 0

        try:
            spritesheet_name = spritesheet_label or os.path.basename(atlas_path)
            renderer = AdobeSpritemapRenderer(
                animation_json_path,
                spritemap_json_path,
                atlas_path,
                filter_single_frame=settings.get(
                    "filter_single_frame_spritemaps", True
                ),
            )
            renderer.ensure_animation_defaults(self.settings_manager, spritesheet_name)
            animations = renderer.build_animation_frames()

            if not animations:
                return {
                    "frames_generated": 0,
                    "anims_generated": 0,
                    "sprites_failed": 0,
                }

            animation_processor = AnimationProcessor(
                animations,
                atlas_path,
                output_dir,
                self.settings_manager,
                self.current_version,
                spritesheet_label=spritesheet_name,
            )
            frames_generated, anims_generated = animation_processor.process_animations()
            return {
                "frames_generated": frames_generated,
                "anims_generated": anims_generated,
                "sprites_failed": 0,
            }
        except Exception as exc:
            sprites_failed += 1
            print(f"[extract_spritemap_project] Error processing {atlas_path}: {exc}")
            return {
                "frames_generated": 0,
                "anims_generated": 0,
                "sprites_failed": sprites_failed,
            }

    def generate_temp_animation_for_preview(
        self,
        atlas_path,
        metadata_path,
        settings,
        animation_name,
        temp_dir=None,
        spritemap_info=None,
        spritesheet_label=None,
    ):
        """Delegate preview generation to `PreviewGenerator` for reuse and clarity."""
        return self.preview_generator.generate_temp_animation(
            atlas_path,
            metadata_path,
            settings,
            animation_name,
            temp_dir=temp_dir,
            spritemap_info=spritemap_info,
            spritesheet_label=spritesheet_label,
        )

    def _handle_unknown_spritesheets_background_detection(
        self, input_dir, spritesheet_list, parent_window
    ):
        """Delegate unknown spritesheet processing to `UnknownSpritesheetHandler`."""
        return self.unknown_handler.handle_background_detection(
            input_dir,
            spritesheet_list,
            parent_window,
        )


class FileProcessorWorker(QThread):
    """Worker thread that continuously pulls files from a queue."""

    file_completed = Signal(str, dict)  # filename, result
    file_failed = Signal(str, str)  # filename, error
    task_started = Signal(str)
    task_finished = Signal(str)

    def __init__(
        self, input_dir, output_dir, parent_window, extractor_instance, task_queue
    ):
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.parent_window = parent_window
        self.extractor = extractor_instance
        self.task_queue = task_queue
        self.current_filename = None

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def run(self):
        """Continuously process files pulled from the shared queue."""
        import threading

        thread_id = threading.get_ident()
        while True:
            filename = self.task_queue.get()
            if filename is None:
                break

            self.current_filename = filename
            self.task_started.emit(filename)
            try:
                self._process_single_file(filename, thread_id)
            finally:
                self.task_finished.emit(filename)
                self.current_filename = None

    def _process_single_file(self, filename, thread_id):
        try:
            relative_path = Path(filename)
            atlas_path = Path(self.input_dir) / relative_path
            atlas_dir = atlas_path.parent
            base_filename = relative_path.stem
            xml_path = atlas_dir / f"{base_filename}.xml"
            txt_path = atlas_dir / f"{base_filename}.txt"
            image_path = str(atlas_path)
            sprite_output_dir = Path(self.output_dir) / relative_path.with_suffix("")
            animation_json_path = atlas_dir / "Animation.json"
            spritemap_json_path = atlas_dir / f"{base_filename}.json"

            os.makedirs(sprite_output_dir, exist_ok=True)
            sprite_output_dir = str(sprite_output_dir)

            has_animation_project = (
                animation_json_path.is_file() and spritemap_json_path.is_file()
            )
            xml_exists = xml_path.is_file()
            txt_exists = txt_path.is_file()
            has_metadata = xml_exists or txt_exists
            metadata_file = str(xml_path) if xml_exists else str(txt_path)
            image_is_supported = filename.lower().endswith(
                (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")
            )

            if (
                not has_animation_project
                and not has_metadata
                and not (os.path.isfile(image_path) and image_is_supported)
            ):
                self.file_failed.emit(filename, "No valid processing path found")
                return

            settings = self.extractor.settings_manager.get_settings(filename)

            if has_animation_project:
                result = self.extractor.extract_spritemap_project(
                    image_path,
                    str(animation_json_path),
                    str(spritemap_json_path),
                    sprite_output_dir,
                    settings,
                    spritesheet_label=filename,
                )
                self.file_completed.emit(filename, result)

            elif has_metadata:
                result = self.extractor.extract_sprites(
                    image_path,
                    metadata_file,
                    sprite_output_dir,
                    settings,
                    None,
                    spritesheet_label=filename,
                )
                self.file_completed.emit(filename, result)

            else:
                result = self.extractor.extract_sprites(
                    image_path,
                    None,
                    sprite_output_dir,
                    settings,
                    None,
                    spritesheet_label=filename,
                )
                self.file_completed.emit(filename, result)

        except Exception as e:
            print(f"[FileProcessorWorker] Error processing {filename}: {str(e)}")
            import traceback

            traceback.print_exc()
            self.file_failed.emit(filename, str(e))
