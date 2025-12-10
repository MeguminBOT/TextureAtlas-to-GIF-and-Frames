#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Base class for tab widget controllers.

Provides a consistent initialization pattern for tab widgets that can
operate in two modes:

1. **Controller mode** (``use_existing_ui=True``): The widget binds to
   pre-existing UI elements created by Qt Designer. It has no parent and
   remains hidden, acting purely as a controller.

2. **Standalone mode** (``use_existing_ui=False``): The widget builds its
   own UI programmatically and can be added to a layout.

Usage:
    from gui.base_tab_widget import BaseTabWidget

    class MyTabWidget(BaseTabWidget):
        def _setup_with_existing_ui(self):
            # Bind to parent_app.ui elements
            ...

        def _build_ui(self):
            # Create UI programmatically
            ...
"""

from __future__ import annotations

from typing import Any, Optional

from PySide6.QtWidgets import QWidget


class BaseTabWidget(QWidget):
    """Base class for tab widgets supporting controller and standalone modes.

    Subclasses must implement:
        - ``_setup_with_existing_ui()``: Bind to existing Qt Designer widgets.
        - ``_build_ui()``: Build the UI programmatically.

    Subclasses may optionally implement:
        - ``_connect_signals()``: Connect signals after UI setup.
        - ``_initialize_state()``: Initialize widget state after setup.

    Attributes:
        parent_app: Reference to the main application window.
        _using_existing_ui: Whether the widget is in controller mode.
    """

    def __init__(
        self,
        parent_app: Optional[Any] = None,
        use_existing_ui: bool = False,
    ):
        """Initialize the tab widget in controller or standalone mode.

        Args:
            parent_app: Main window object providing config, UI, and signals.
            use_existing_ui: When ``True``, bind to widgets from Qt Designer
                instead of building the layout programmatically.
        """
        self._using_existing_ui = self._should_use_existing_ui(
            parent_app, use_existing_ui
        )

        if self._using_existing_ui:
            # Controller mode: no parent, hidden widget
            super().__init__(None)
            self.hide()
        else:
            # Standalone mode: normal parented widget
            super().__init__(parent_app)

        self.parent_app = parent_app

    def _should_use_existing_ui(
        self, parent_app: Optional[Any], use_existing_ui: bool
    ) -> bool:
        """Determine if existing UI should be used.

        Override this method to customize the detection logic.

        Args:
            parent_app: The parent application reference.
            use_existing_ui: The requested mode.

        Returns:
            True if existing UI is available and should be used.
        """
        return bool(use_existing_ui and parent_app and hasattr(parent_app, "ui"))

    def _setup_ui(self):
        """Set up the UI based on the current mode.

        Call this method in subclass ``__init__`` after initializing
        subclass-specific state but before connecting signals.
        """
        if self._using_existing_ui:
            self._setup_with_existing_ui()
        else:
            self._build_ui()

    def _setup_with_existing_ui(self):
        """Bind to widgets created by Qt Designer.

        Subclasses must override this method to bind ``self.parent_app.ui``
        elements to local attributes.

        Raises:
            NotImplementedError: Always raised in base class; subclasses must
                override.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _setup_with_existing_ui()"
        )

    def _build_ui(self):
        """Build the UI programmatically.

        Subclasses must override this method to create layouts and widgets
        when not using existing UI.

        Raises:
            NotImplementedError: Always raised in base class; subclasses must
                override.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _build_ui()"
        )

    def _connect_signals(self):
        """Connect signals after UI setup.

        Optional: Subclasses can override to connect widget signals.
        """
        pass

    def _initialize_state(self):
        """Initialize widget state after setup.

        Optional: Subclasses can override to set initial values.
        """
        pass
