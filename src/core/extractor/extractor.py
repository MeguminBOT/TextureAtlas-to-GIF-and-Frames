"""Multi-threaded spritesheet extraction orchestrator.

This module provides ``Extractor``, which coordinates worker threads to
process batches of spritesheets in parallel. It also defines
``FileProcessorWorker`` (a ``QThread`` subclass) and the
``ExtractionCancelled`` exception.

Type Aliases:
    ProgressCallback: ``Callable[[int, int, str], None]`` for progress updates.
    StatisticsCallback: ``Callable[[int, int, int], None]`` for totals.
    ErrorPromptCallback: ``Callable[[str, BaseException], bool]`` for error prompts.
    StatsUpdate: Dict payload carrying counter deltas between threads.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from queue import SimpleQueue, Empty
from threading import Event, Lock
from typing import Any, Callable, Dict, List, Optional, Sequence

from PySide6.QtCore import QCoreApplication, QThread, Signal

# Import our own modules
from core.extractor.atlas_processor import AtlasProcessor
from core.extractor.sprite_processor import SpriteProcessor
from core.extractor.animation_processor import AnimationProcessor
from core.extractor.preview_generator import PreviewGenerator
from core.extractor.spritemap import AdobeSpritemapRenderer
from core.extractor.unknown_spritesheet_handler import UnknownSpritesheetHandler
from utils.utilities import Utilities

ProgressCallback = Callable[[int, int, str], None]
StatisticsCallback = Callable[[int, int, int], None]
ErrorPromptCallback = Callable[[str, BaseException], bool]
StatsUpdate = Dict[str, Any]


class ExtractionCancelled(Exception):
    """Raised when extraction is cancelled by the user or due to a fatal error."""

    pass


class Extractor:
    """Orchestrate parallel spritesheet parsing and animation export.

    Manages a pool of ``FileProcessorWorker`` threads, dispatches files from
    a queue, aggregates statistics, and supports pause/cancel semantics.

    Attributes:
        settings_manager: Provides per-spritesheet and global settings.
        progress_callback: Invoked with ``(current, total, status)`` during runs.
        statistics_callback: Invoked with ``(frames, anims, failed)`` totals.
        current_version: Version string embedded in exported metadata.
        app_config: Optional application configuration for resource limits.
        cancel_event: ``Event`` signalling cancellation requests.
        preview_generator: Helper for generating animation previews.
        unknown_handler: Handles spritesheets without recognised metadata.
    """

    def __init__(
        self,
        progress_callback,
        current_version,
        settings_manager,
        app_config=None,
        statistics_callback=None,
        cancel_event=None,
        error_prompt_callback=None,
    ):
        """Initialise the extractor with callbacks and configuration.

        Args:
            progress_callback: Callable receiving ``(current, total, status)``.
            current_version: Version string for file metadata.
            settings_manager: Settings provider for export options.
            app_config: Optional config with resource limit overrides.
            statistics_callback: Optional callable receiving totals after runs.
            cancel_event: Optional ``Event`` for signalling cancellation.
            error_prompt_callback: Optional callback for error prompts.
        """
        self.settings_manager = settings_manager
        self.progress_callback = progress_callback
        self.statistics_callback = statistics_callback
        self.current_version = current_version
        self.app_config = app_config
        self.cancel_event = cancel_event or Event()
        self.error_prompt_callback = error_prompt_callback
        self._cancel_reason = None
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
        self._pause_event = Event()
        self._pause_event.set()
        self._awaiting_error_decision = False
        self._error_prompt_lock = Lock()

    def process_directory(
        self,
        input_dir,
        output_dir,
        progress_callback=None,
        parent_window=None,
        spritesheet_list=None,
    ):
        """Process a batch of spritesheets using a worker pool.

        Enqueues files, starts workers, monitors progress, and aggregates
        statistics until all work completes or cancellation is requested.

        Args:
            input_dir: Root directory containing source atlas files.
            output_dir: Destination directory for exported assets.
            progress_callback: Optional override for instance callback.
            parent_window: Optional parent for modal dialogs.
            spritesheet_list: Iterable of relative filenames to process.

        Raises:
            ExtractionCancelled: If the run is aborted mid-flight.
        """

        self._initialize_processing_state()
        self._raise_if_cancelled()
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
        self._raise_if_cancelled()

        if self.statistics_callback:
            self.statistics_callback(
                self.total_frames_generated,
                self.total_anims_generated,
                self.total_sprites_failed,
            )

    def _initialize_processing_state(self):
        """Reset counters, queues, and events before processing a new batch."""
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
        """Return an explicit override or fall back to the instance callback.

        Args:
            override_callback: Caller-supplied callback, or ``None``.

        Returns:
            The override if provided, otherwise ``self.progress_callback``.
        """
        return self.progress_callback or override_callback

    def _resolve_cpu_threads(self) -> int:
        """Resolve how many worker threads to spin up based on config and hardware.

        Returns:
            int: Planned worker count honoring ``app_config`` constraints.
        """
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
        """Return the smaller of available threads and pending files.

        Args:
            cpu_threads: Maximum threads allowed by hardware/config.
            file_count: Number of files queued for processing.

        Returns:
            Worker count capped to avoid idle threads.
        """
        return min(cpu_threads, file_count)

    def _start_worker_pool(
        self,
        max_threads,
        input_dir,
        output_dir,
        parent_window,
    ):
        """Spawn worker threads and wire up their signals.

        Args:
            max_threads: Number of workers to create.
            input_dir: Root folder for atlas files.
            output_dir: Destination folder for exports.
            parent_window: UI parent for modal dialogs.
        """
        if not max_threads:
            return

        self._planned_worker_count = max_threads

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

    def _monitor_workers(self) -> None:
        """Drain statistics queue and update progress until workers finish.

        Uses blocking waits with timeouts to reduce idle spin while keeping
        the UI responsive. Exits once all workers signal completion and the
        stats queue is empty.
        """
        while True:
            if self.cancel_event.is_set():
                self._capture_cancel_reason()
                self._wake_workers()
            processed = self._drain_stats_queue()
            if not processed:
                timeout = self._compute_wait_timeout()
                if self.cancel_event.is_set():
                    timeout = min(timeout, 0.02)
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
    def _process_qt_events() -> None:
        """Pump pending UI events so the interface stays responsive."""
        app = QCoreApplication.instance()
        if app is not None:
            QCoreApplication.processEvents()

    def _maybe_process_qt_events(self, *, force: bool = False) -> None:
        """Throttle event processing so high-volume batches do not starve the UI.

        Args:
            force: When ``True``, bypass throttling and pump events immediately.
        """
        now = time.monotonic()
        if force or (now - self._last_qt_event_pump) >= self._qt_event_interval:
            self._process_qt_events()
            self._last_qt_event_pump = now

    def _compute_wait_timeout(self) -> float:
        """Pick the next wait duration based on queued work and worker state.

        Returns:
            Timeout in seconds, shorter when work is in progress.
        """
        active_tasks = len(self.work_in_progress)
        if active_tasks:
            return 0.015
        if self.active_workers:
            return 0.05
        return 0.08

    def _finalize_directory_processing(self) -> None:
        """Capture timing and aggregate stats once all workers have stopped.

        Stores elapsed duration and totals in instance attributes for later
        retrieval by UI components or diagnostics.
        """
        end_time = time.time()
        duration = end_time - self.start_time
        self._last_processing_finished = end_time
        self._last_processing_duration = duration
        self._last_processing_totals = (
            self.total_frames_generated,
            self.total_anims_generated,
            self.total_sprites_failed,
        )

    def request_cancel(self, reason: Optional[str] = None) -> None:
        """Set the cancel flag, wake workers, and optionally note the reason.

        Args:
            reason (str | None): Human-readable message describing why work stopped.
        """
        if reason and not self._cancel_reason:
            self._cancel_reason = reason
        if reason:
            setattr(self.cancel_event, "reason", reason)
        if self.cancel_event.is_set():
            self._wake_workers()
            return
        self.cancel_event.set()
        self._resume_workers()
        self._wake_workers()

    def _capture_cancel_reason(self) -> None:
        """Mirror the event's reason attribute so we can surface it later."""
        if self.cancel_event.is_set() and not self._cancel_reason:
            self._cancel_reason = getattr(self.cancel_event, "reason", None)

    def _wake_workers(self) -> None:
        """Push sentinel work items so blocked workers break out quickly."""
        if getattr(self, "file_queue", None) is None:
            return
        if getattr(self, "_cancel_wake_sent", False):
            return
        sentinel_count = (
            self._planned_worker_count or len(getattr(self, "active_workers", [])) or 1
        )
        try:
            for _ in range(sentinel_count):
                self.file_queue.put(None)
        finally:
            self._cancel_wake_sent = True

    def _raise_if_cancelled(self) -> None:
        """Abort the current operation if a cancellation was requested."""
        if self.cancel_event.is_set():
            self._capture_cancel_reason()
            reason = self._cancel_reason or "Processing cancelled"
            raise ExtractionCancelled(reason)

    def wait_for_resume(self) -> bool:
        """Block workers while paused and exit early if cancellation occurs.

        Returns:
            bool: ``True`` when resume occurs, ``False`` if cancellation intervenes.
        """
        while True:
            if self.cancel_event.is_set():
                return False
            if self._pause_event.wait(timeout=0.05):
                if self.cancel_event.is_set():
                    return False
                return True

    def _pause_workers(self) -> None:
        """Clear the pause event so workers temporarily yield the CPU."""
        if self._pause_event.is_set():
            self._pause_event.clear()

    def _resume_workers(self) -> None:
        """Allow paused workers to resume by setting the pause event."""
        if not self._pause_event.is_set():
            self._pause_event.set()

    def _handle_worker_error_prompt(self, filename: str, error: BaseException) -> bool:
        """Synchronously ask the UI whether processing should continue after errors.

        Args:
            filename (str): File being processed when the failure occurred.
            error (BaseException): Exception raised by the worker thread.

        Returns:
            bool: ``True`` when the user chooses to continue, ``False`` otherwise.
        """
        if not self.error_prompt_callback:
            return False
        with self._error_prompt_lock:
            if self._awaiting_error_decision:
                return False
            self._awaiting_error_decision = True

        continue_processing = False
        try:
            self._pause_workers()
            continue_processing = bool(self.error_prompt_callback(filename, error))
        except Exception as prompt_exc:
            print(
                f"[_handle_worker_error_prompt] Failed to prompt on error: {prompt_exc}"
            )
            continue_processing = False
        finally:
            with self._error_prompt_lock:
                self._awaiting_error_decision = False
            if continue_processing:
                self._resume_workers()

        return continue_processing

    def _queue_stats_update(
        self,
        *,
        frames_delta: int = 0,
        anims_delta: int = 0,
        failed_delta: int = 0,
        processed_delta: int = 1,
        debug_message: Optional[str] = None,
    ) -> None:
        """Push a stats delta into the queue consumed by the monitor thread.

        Args:
            frames_delta (int): Change in exported frame count.
            anims_delta (int): Change in exported animation count.
            failed_delta (int): Change in failure count.
            processed_delta (int): Increment applied to processed file count.
            debug_message (str | None): Optional trace string for verbose logging.
        """

        update: StatsUpdate = {
            "frames_delta": frames_delta,
            "anims_delta": anims_delta,
            "failed_delta": failed_delta,
            "processed_delta": processed_delta,
            "debug_message": debug_message,
        }
        self._stats_queue.put(update)
        if hasattr(self, "_stats_available_event"):
            self._stats_available_event.set()

    def _drain_stats_queue(self) -> bool:
        """Flush pending stats updates and apply them sequentially.

        Returns:
            bool: ``True`` when at least one update was processed.
        """
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

    def _stats_queue_empty(self) -> bool:
        """Return ``True`` when no pending stats updates remain."""
        return self._stats_queue.empty()

    def _apply_stats_update(self, update: StatsUpdate) -> None:
        """Update global counters and emit statistics callbacks for a delta.

        Args:
            update (StatsUpdate): Queued dictionary describing counter deltas.
        """

        frames_delta = int(update.get("frames_delta", 0))
        anims_delta = int(update.get("anims_delta", 0))
        failed_delta = int(update.get("failed_delta", 0))

        processed_delta = int(update.get("processed_delta", 0))

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

    def _on_worker_task_started(self, worker: QThread, filename: str) -> None:
        """Record which worker claimed a file so progress summaries stay accurate.

        Args:
            worker (QThread): Worker instance that began processing.
            filename (str): Path claimed by the worker.
        """
        if worker:
            self.work_in_progress[worker] = filename
        if filename:
            self._last_started_file = str(filename)
        self._progress_dirty = True
        self._update_progress_text(force=True)

    def _on_worker_task_finished(self, worker: QThread, filename: str) -> None:
        """Drop worker bookkeeping once a file completes.

        Args:
            worker: Worker instance that finished its task.
            filename: Path that was being processed.
        """
        if worker in self.work_in_progress:
            self.work_in_progress.pop(worker, None)
        self._progress_dirty = True
        self._update_progress_text(force=True)

    def _update_progress_text(self, *, force: bool = False) -> None:
        """Emit throttled progress updates with human-friendly worker summaries.

        Args:
            force: When ``True``, bypass throttling and emit immediately.
        """
        if not self._progress_callback:
            return

        if not force and not self._progress_dirty:
            return

        now = time.monotonic()
        if (
            not force
            and (now - self._last_progress_emit) < self._progress_emit_interval
        ):
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

    def _build_worker_status_snapshot(self, limit: int = 4) -> Dict[str, Any]:
        """Capture a structured snapshot of worker state for the UI overlay.

        Args:
            limit: Maximum number of workers to include in the ``workers`` list.

        Returns:
            Dictionary containing ``summary``, ``workers``, and metadata keys.
        """
        worker_rows: List[Dict[str, Any]] = []
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
        recent_display = Path(recent_full_path).name if recent_full_path else None

        return {
            "summary": summary,
            "workers": worker_rows,
            "hidden_count": 0,
            "worker_count": worker_count,
            "recent_full_path": recent_full_path,
            "recent_display": recent_display,
        }

    @staticmethod
    def _format_worker_summary(processing_count: int, worker_count: int) -> str:
        """Format a concise summary string describing worker utilization.

        Args:
            processing_count: Number of workers currently processing files.
            worker_count: Total number of active worker threads.

        Returns:
            Human-readable status like "2 workers running (of 4 total workers)".
        """
        running_plural = "s" if processing_count != 1 else ""
        total_plural = "s" if worker_count != 1 else ""
        return (
            f"{processing_count} worker{running_plural} running "
            f"(of {worker_count} total worker{total_plural})"
        )

    def _on_file_completed(
        self, filename: str, result: Optional[Dict[str, int]]
    ) -> None:
        """Handle successful file completion by relaying stats deltas.

        Args:
            filename (str): Processed file path.
            result (dict[str, int] | None): Result payload from the worker thread.
        """
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

    def _on_file_failed(self, filename: str, error: BaseException | str) -> None:
        """Handle file processing failure and decide whether to abort.

        Args:
            filename (str): File that failed to process.
            error (BaseException | str): Failure details for logging and prompts.
        """
        print(f"Error processing {filename}: {error}")

        self._queue_stats_update(failed_delta=1, processed_delta=1)
        if self._handle_worker_error_prompt(filename, error):
            return

        reason_template = QCoreApplication.translate(
            self.__class__.__name__,
            "Processing halted due to an error in {filename}",
        )
        self.request_cancel(reason=reason_template.format(filename=Path(filename).name))

    def _worker_finished(self, worker: QThread) -> None:
        """Handle worker shutdown once it has consumed its sentinel.

        Args:
            worker (QThread): Worker thread that just emitted ``finished``.
        """
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
        atlas_path: str,
        metadata_path: Optional[str],
        output_dir: str,
        settings: Dict[str, Any],
        parent_window: Optional[Any] = None,
        spritesheet_label: Optional[str] = None,
    ) -> Dict[str, int]:
        """Extract sprites and animations from a standard atlas + metadata pair.

        Args:
            atlas_path (str): Path to the source atlas image.
            metadata_path (str | None): Path to metadata or ``None`` for autodetect.
            output_dir (str): Directory receiving exported assets.
            settings (dict): Overrides controlling exports.
            parent_window (Any | None): Parent object for any prompts.
            spritesheet_label (str | None): Friendly name overriding file stem.

        Returns:
            dict[str, int]: Result dictionary containing frame/animation totals and failures.
        """
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
            return {
                "frames_generated": frames_generated,
                "anims_generated": anims_generated,
                "sprites_failed": sprites_failed,
            }

        except Exception as general_error:
            sprites_failed += 1
            print(
                f"[extract_sprites] Exception for {atlas_path}: {str(general_error)}, sprites_failed = {sprites_failed}"
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
        atlas_path: str,
        animation_json_path: str,
        spritemap_json_path: str,
        output_dir: str,
        settings: Dict[str, Any],
        spritesheet_label: Optional[str] = None,
    ) -> Dict[str, int]:
        """Process an Adobe Spritemap project (Animation.json + per-sheet JSON).

        Args:
            atlas_path (str): Path to atlas image referenced by the project.
            animation_json_path (str): Path to Animation.json.
            spritemap_json_path (str): Path to the per-spritesheet JSON.
            output_dir (str): Directory where exports are stored.
            settings (dict): User overrides controlling export behavior.
            spritesheet_label (str | None): Optional friendly label.

        Returns:
            dict[str, int]: Counts dictionary similar to ``extract_sprites``.
        """
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
        atlas_path: str,
        metadata_path: Optional[str],
        settings: Dict[str, Any],
        animation_name: str,
        temp_dir: Optional[str] = None,
        spritemap_info: Optional[Dict[str, Any]] = None,
        spritesheet_label: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a temporary animation file for UI preview.

        Delegates to ``PreviewGenerator`` so preview logic is reusable.

        Args:
            atlas_path: Path to the source atlas.
            metadata_path: Path to metadata, or ``None`` for unknown sheets.
            settings: Export options dict.
            animation_name: Name of the animation to preview.
            temp_dir: Directory for the temporary file.
            spritemap_info: Optional Adobe spritemap project info.
            spritesheet_label: Friendly display name.

        Returns:
            Path to the generated preview file, or ``None`` on failure.
        """
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
        self,
        input_dir: str,
        spritesheet_list: Sequence[str],
        parent_window: Optional[Any],
    ) -> Optional[Dict[str, Any]]:
        """Detect background colours for unknown spritesheets.

        Args:
            input_dir: Root directory containing the images.
            spritesheet_list: Filenames to analyse.
            parent_window: UI parent for dialogs.

        Returns:
            Detection results dict, or ``None`` if skipped.
        """
        return self.unknown_handler.handle_background_detection(
            input_dir,
            spritesheet_list,
            parent_window,
        )


class FileProcessorWorker(QThread):
    """Worker thread that pulls filenames from a queue and processes them.

    Emits Qt signals on completion or failure so the main thread can update
    statistics and progress displays.

    Signals:
        file_completed: ``(filename, result_dict)`` on success.
        file_failed: ``(filename, error_str)`` on failure.
        task_started: ``(filename)`` when a file is claimed.
        task_finished: ``(filename)`` when processing ends.
    """

    file_completed = Signal(str, dict)  # filename, result
    file_failed = Signal(str, object)  # filename, error detail
    task_started = Signal(str)
    task_finished = Signal(str)

    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        parent_window: Optional[Any],
        extractor_instance: Extractor,
        task_queue: SimpleQueue,
    ) -> None:
        """Wire worker thread to shared queues and parent extractor instance.

        Args:
            input_dir (str): Root folder containing atlas files.
            output_dir (str): Destination folder for exported assets.
            parent_window (Any | None): UI parent used for modal dialogs.
            extractor_instance (Extractor): Owning extractor orchestrator.
            task_queue (SimpleQueue): Queue of filenames plus sentinels.
        """
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.parent_window = parent_window
        self.extractor = extractor_instance
        self.task_queue = task_queue
        self.current_filename = None

    def tr(self, text: str) -> str:
        """Translate a string using the Qt internationalization system.

        Args:
            text: Source string to translate.

        Returns:
            Translated string, or the original if no translation exists.
        """
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def run(self) -> None:
        """Pull files from the queue until a sentinel or cancellation.

        Emits ``task_started`` and ``task_finished`` around each file.
        Exits cleanly when the extractor requests cancellation.
        """
        import threading

        thread_id = threading.get_ident()
        while True:
            if not self.extractor.wait_for_resume():
                break

            filename = self.task_queue.get()
            if filename is None or self.extractor.cancel_event.is_set():
                break

            self.current_filename = filename
            self.task_started.emit(filename)
            try:
                if self.extractor.cancel_event.is_set():
                    break
                self._process_single_file(filename, thread_id)
            finally:
                self.task_finished.emit(filename)
                self.current_filename = None

            if self.extractor.cancel_event.is_set():
                break

    def _process_single_file(self, filename: str, thread_id: int) -> None:
        """Process a single atlas file or spritemap project pulled from the queue.

        Args:
            filename (str): Relative filename as enqueued by the orchestrator.
            thread_id (int): Worker thread identifier, useful for diagnostics.
        """
        if self.extractor.cancel_event.is_set():
            return
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
            self.file_failed.emit(filename, e)
