from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Signal


class BackgroundTaskSignals(QObject):
    """Signals emitted by background translation tasks."""

    completed = Signal(object)
    failed = Signal(str)


class BackgroundTaskWorker(QRunnable):
    """Run long translation tasks without blocking the UI thread."""

    def __init__(self, fn: Callable[..., Any], *args: object, **kwargs: object) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = BackgroundTaskSignals()

    def run(self) -> None:  # pragma: no cover - GUI threading code
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # Surface message back to UI
            self.signals.failed.emit(str(exc))
        else:
            self.signals.completed.emit(result)


__all__ = ["BackgroundTaskWorker", "BackgroundTaskSignals"]
