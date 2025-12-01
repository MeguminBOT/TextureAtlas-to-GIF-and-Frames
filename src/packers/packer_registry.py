#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Registry for packer algorithms.

Provides centralized access to all packing algorithms with dynamic registration.
Follows the same pattern as the exporter registry for consistency.

Usage:
    from packers.packer_registry import PackerRegistry, register_packer

    # Get all available packers
    all_packers = PackerRegistry.get_all_algorithms()

    # Get a specific packer by algorithm name
    packer = PackerRegistry.get_packer("maxrects")
    packer.set_heuristic("bssf")
    result = packer.pack(frames)

    # Use convenience function
    result = PackerRegistry.pack("guillotine", frames, options)

    # Register a custom packer
    @register_packer
    class MyCustomPacker(BasePacker):
        ALGORITHM_NAME = "custom"
        ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Type

from packers.packer_types import (
    FrameInput,
    PackerError,
    PackerOptions,
    PackerResult,
)

if TYPE_CHECKING:
    from packers.base_packer import BasePacker


class PackerRegistry:
    """Central registry for all packing algorithms.

    Provides methods to register, retrieve, and instantiate packers by their
    algorithm name. Supports dynamic registration via decorator.

    Attributes:
        _registry: Internal mapping of algorithm names to packer classes.
    """

    _registry: Dict[str, Type[BasePacker]] = {}

    @classmethod
    def register(cls, packer_class: Type[BasePacker]) -> Type[BasePacker]:
        """Register a packer class.

        Args:
            packer_class: Packer class with ALGORITHM_NAME attribute.

        Returns:
            The packer class unchanged (allows use as decorator).

        Raises:
            ValueError: If packer lacks ALGORITHM_NAME or name is duplicate.
        """
        if not hasattr(packer_class, "ALGORITHM_NAME"):
            raise ValueError(
                f"Packer class {packer_class.__name__} must have ALGORITHM_NAME"
            )

        name = packer_class.ALGORITHM_NAME
        if name in cls._registry:
            raise ValueError(f"Packer '{name}' is already registered")

        cls._registry[name] = packer_class
        return packer_class

    @classmethod
    def unregister(cls, algorithm_name: str) -> bool:
        """Remove a packer from the registry.

        Args:
            algorithm_name: Name of the algorithm to remove.

        Returns:
            True if removed, False if not found.
        """
        if algorithm_name in cls._registry:
            del cls._registry[algorithm_name]
            return True
        return False

    @classmethod
    def get_packer(
        cls,
        algorithm_name: str,
        options: Optional[PackerOptions] = None,
    ) -> BasePacker:
        """Get an instance of a packer by algorithm name.

        Args:
            algorithm_name: Name of the packing algorithm.
            options: Optional packer configuration.

        Returns:
            Instantiated packer ready for use.

        Raises:
            PackerError: If algorithm name is not found.
        """
        if algorithm_name not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys()))
            raise PackerError(
                f"Unknown packer algorithm: '{algorithm_name}'. "
                f"Available: {available}"
            )

        packer_class = cls._registry[algorithm_name]
        return packer_class(options)

    @classmethod
    def get_packer_class(cls, algorithm_name: str) -> Optional[Type[BasePacker]]:
        """Get the packer class without instantiating.

        Args:
            algorithm_name: Name of the packing algorithm.

        Returns:
            Packer class or None if not found.
        """
        return cls._registry.get(algorithm_name)

    @classmethod
    def get_all_algorithms(cls) -> List[Dict[str, str]]:
        """Get information about all registered packers.

        Returns:
            List of dicts with 'name', 'display_name', and 'heuristics' keys.
        """
        result = []
        for name, packer_class in sorted(cls._registry.items()):
            info = {
                "name": name,
                "display_name": getattr(
                    packer_class, "DISPLAY_NAME", name.replace("-", " ").title()
                ),
                "heuristics": getattr(packer_class, "SUPPORTED_HEURISTICS", []),
            }
            result.append(info)
        return result

    @classmethod
    def get_algorithm_names(cls) -> List[str]:
        """Get list of all registered algorithm names.

        Returns:
            Sorted list of algorithm names.
        """
        return sorted(cls._registry.keys())

    @classmethod
    def pack(
        cls,
        algorithm_name: str,
        frames: List[FrameInput],
        options: Optional[PackerOptions] = None,
        heuristic: Optional[str] = None,
    ) -> PackerResult:
        """Convenience method to pack frames with a specific algorithm.

        Args:
            algorithm_name: Name of the packing algorithm.
            frames: List of frames to pack.
            options: Optional packer configuration.
            heuristic: Optional heuristic key to set.

        Returns:
            PackerResult with packed frames and metadata.
        """
        packer = cls.get_packer(algorithm_name, options)

        if heuristic:
            packer.set_heuristic(heuristic)

        return packer.pack(frames)

    @classmethod
    def is_registered(cls, algorithm_name: str) -> bool:
        """Check if an algorithm is registered.

        Args:
            algorithm_name: Name to check.

        Returns:
            True if registered, False otherwise.
        """
        return algorithm_name in cls._registry

    @classmethod
    def clear(cls) -> None:
        """Clear all registered packers. Useful for testing."""
        cls._registry.clear()

    @classmethod
    def register_defaults(cls) -> None:
        """Register all default packers.

        This imports and registers all built-in packer implementations.
        Call this at module load time or application startup.
        """
        # Import all packer modules to trigger registration
        # Using local imports to avoid circular dependencies
        from packers.maxrects_packer import MaxRectsPacker
        from packers.guillotine_packer import GuillotinePacker
        from packers.skyline_packer import SkylinePacker
        from packers.shelf_packer import ShelfPacker, ShelfPackerDecreasingHeight
        from packers.base_packer import SimplePacker

        # Register if not already registered (allows re-import)
        for packer_cls in [
            MaxRectsPacker,
            GuillotinePacker,
            SkylinePacker,
            ShelfPacker,
            ShelfPackerDecreasingHeight,
            SimplePacker,
        ]:
            if not cls.is_registered(packer_cls.ALGORITHM_NAME):
                cls.register(packer_cls)


def register_packer(cls: Type[BasePacker]) -> Type[BasePacker]:
    """Decorator to register a packer class with the registry.

    Usage:
        @register_packer
        class MyPacker(BasePacker):
            ALGORITHM_NAME = "my-packer"
            ...
    """
    PackerRegistry.register(cls)
    return cls


def get_packer(
    algorithm_name: str,
    options: Optional[PackerOptions] = None,
) -> BasePacker:
    """Convenience function to get a packer instance.

    Args:
        algorithm_name: Name of the packing algorithm.
        options: Optional packer configuration.

    Returns:
        Instantiated packer.
    """
    return PackerRegistry.get_packer(algorithm_name, options)


def pack(
    algorithm_name: str,
    frames: List[FrameInput],
    options: Optional[PackerOptions] = None,
    heuristic: Optional[str] = None,
) -> PackerResult:
    """Convenience function to pack frames.

    Args:
        algorithm_name: Name of the packing algorithm.
        frames: List of frames to pack.
        options: Optional packer configuration.
        heuristic: Optional heuristic to use.

    Returns:
        PackerResult with packed frames.
    """
    return PackerRegistry.pack(algorithm_name, frames, options, heuristic)


def list_algorithms() -> List[Dict[str, str]]:
    """List all available packing algorithms.

    Returns:
        List of algorithm info dicts.
    """
    return PackerRegistry.get_all_algorithms()


def get_heuristics_for_algorithm(algorithm_name: str) -> List[tuple]:
    """Get available heuristics for a specific algorithm.

    Args:
        algorithm_name: Name of the algorithm.

    Returns:
        List of (key, display_name) tuples for available heuristics.
    """
    packer_class = PackerRegistry.get_packer_class(algorithm_name)
    if packer_class is None:
        return []
    return getattr(packer_class, "SUPPORTED_HEURISTICS", [])


# Register default packers when module is imported
# This ensures all built-in packers are available immediately
def _init_registry() -> None:
    """Initialize the registry with default packers."""
    try:
        PackerRegistry.register_defaults()
    except ImportError:
        # Some packers may not be available yet during initial import
        pass


_init_registry()


__all__ = [
    "PackerRegistry",
    "register_packer",
    "get_packer",
    "pack",
    "list_algorithms",
    "get_heuristics_for_algorithm",
]
