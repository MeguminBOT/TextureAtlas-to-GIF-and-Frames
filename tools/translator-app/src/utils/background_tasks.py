"""Qt-compatible workers for running tasks off the main thread.

Provides a QRunnable wrapper that executes a callable in the thread pool
and emits signals on completion or failure.
"""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Signal


class BackgroundTaskSignals(QObject):
    """Signals emitted by background translation tasks.

    Attributes:
        completed: Emitted with the result on successful completion.
        failed: Emitted with an error message on failure.
    """

    completed = Signal(object)
    failed = Signal(str)


class BackgroundTaskWorker(QRunnable):
    """Run a callable in the Qt thread pool without blocking the UI.

    Attributes:
        fn: The callable to execute.
        args: Positional arguments for the callable.
        kwargs: Keyword arguments for the callable.
        signals: Signals for reporting success or failure.
    """

    def __init__(self, fn: Callable[..., Any], *args: object, **kwargs: object) -> None:
        """Initialize the worker with a callable and its arguments.

        Args:
            fn: The function to run in the background.
            *args: Positional arguments for fn.
            **kwargs: Keyword arguments for fn.
        """
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = BackgroundTaskSignals()

    def run(self) -> None:  # pragma: no cover - GUI threading code
        """Execute the callable and emit success or failure signals."""
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # Surface message back to UI
            self.signals.failed.emit(str(exc))
        else:
            self.signals.completed.emit(result)


__all__ = ["BackgroundTaskWorker", "BackgroundTaskSignals"]
