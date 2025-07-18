#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
import numpy as np
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import time


class PackingAlgorithm(Enum):
    """Available packing algorithms."""
    NONE = 0          # No optimization - simple grid
    BOTTOM_LEFT = 1   # Bottom-left fill
    BEST_FIT = 2      # Best area fit
    BEST_SHORT = 3    # Best short side fit
    BEST_LONG = 4     # Best long side fit
    BEST_AREA = 5     # Best area with rotation
    SKYLINE = 6       # Skyline bottom-left
    MAXRECTS = 7      # MaxRects with all heuristics


@dataclass
class Frame:
    """Represents a single frame in the atlas."""
    name: str
    image_path: str
    width: int
    height: int
    x: int = 0
    y: int = 0
    rotated: bool = False
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    @property
    def perimeter(self) -> int:
        return 2 * (self.width + self.height)


@dataclass
class AtlasSettings:
    """Configuration for atlas generation."""
    max_size: int = 2048
    min_size: int = 128
    padding: int = 2
    power_of_2: bool = True
    optimization_level: int = 5
    allow_rotation: bool = True
    efficiency_factor: float = 1.3
    
    @property
    def algorithm(self) -> PackingAlgorithm:
        """Get packing algorithm based on optimization level."""
        if self.optimization_level == 0:
            return PackingAlgorithm.NONE
        elif self.optimization_level <= 2:
            return PackingAlgorithm.BOTTOM_LEFT
        elif self.optimization_level <= 4:
            return PackingAlgorithm.BEST_FIT
        elif self.optimization_level <= 6:
            return PackingAlgorithm.BEST_SHORT
        elif self.optimization_level <= 8:
            return PackingAlgorithm.SKYLINE
        else:
            return PackingAlgorithm.MAXRECTS


class Rectangle:
    """Simple rectangle class for packing."""
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    @property
    def right(self) -> int:
        return self.x + self.width
    
    @property
    def bottom(self) -> int:
        return self.y + self.height
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    def intersects(self, other: 'Rectangle') -> bool:
        return not (self.right <= other.x or other.right <= self.x or 
                   self.bottom <= other.y or other.bottom <= self.y)


class SparrowAtlasGenerator:
    """
    Fast and efficient texture atlas generator specifically for Sparrow format.
    Optimized for speed and tight packing with configurable optimization levels.
    """
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
        self.frames: List[Frame] = []
        self.used_rectangles: List[Rectangle] = []
        self.free_rectangles: List[Rectangle] = []
        
    def generate_atlas(self, animation_groups: Dict[str, List[str]], 
                      output_path: str, settings: AtlasSettings) -> Dict:
        """
        Generate a Sparrow format texture atlas.
        
        Args:
            animation_groups: Dictionary mapping animation names to frame file paths
            output_path: Path for output files (without extension)
            settings: Atlas generation settings
            
        Returns:
            Dictionary containing generation results
        """
        start_time = time.time()
        
        try:
            # Step 1: Load and prepare frames
            self._update_progress(0, 5, "Loading frames...")
            self._load_frames(animation_groups)
            
            if not self.frames:
                return {'success': False, 'error': 'No frames to pack'}
            
            # Step 2: Sort frames for optimal packing
            self._update_progress(1, 5, "Sorting frames...")
            self._sort_frames(settings)
            
            # Step 3: Calculate optimal atlas size
            self._update_progress(2, 5, "Calculating atlas size...")
            atlas_width, atlas_height = self._calculate_atlas_size(settings)
            
            # Step 4: Pack frames into atlas
            self._update_progress(3, 5, "Packing frames...")
            if not self._pack_frames(atlas_width, atlas_height, settings):
                return {'success': False, 'error': 'Could not fit all frames in atlas'}
            
            # Step 5: Generate output files
            self._update_progress(4, 5, "Generating output...")
            atlas_image = self._create_atlas_image(atlas_width, atlas_height)
            xml_content = self._generate_sparrow_xml(output_path, atlas_width, atlas_height)
            
            # Save files
            image_path = f"{output_path}.png"
            xml_path = f"{output_path}.xml"
            
            atlas_image.save(image_path, "PNG")
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            self._update_progress(5, 5, "Complete!")
            
            generation_time = time.time() - start_time
            
            return {
                'success': True,
                'atlas_path': image_path,
                'xml_path': xml_path,
                'atlas_size': (atlas_width, atlas_height),
                'frame_count': len(self.frames),
                'frames_count': len(self.frames),  # Alternative key for compatibility
                'generation_time': generation_time,
                'efficiency': self._calculate_efficiency(atlas_width, atlas_height),
                'metadata_files': [xml_path]  # For compatibility with UI
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _load_frames(self, animation_groups: Dict[str, List[str]]):
        """Load frame images and extract metadata."""
        self.frames = []
        
        for animation_name, frame_paths in animation_groups.items():
            for i, frame_path in enumerate(frame_paths):
                try:
                    with Image.open(frame_path) as img:
                        frame_name = f"{animation_name}_{i:04d}"
                        frame = Frame(
                            name=frame_name,
                            image_path=frame_path,
                            width=img.width,
                            height=img.height
                        )
                        self.frames.append(frame)
                except Exception as e:
                    print(f"Error loading frame {frame_path}: {e}")
                    continue
    
    def _sort_frames(self, settings: AtlasSettings):
        """Sort frames for optimal packing based on optimization level."""
        if settings.optimization_level == 0:
            # No sorting - keep original order
            return
        elif settings.optimization_level <= 3:
            # Simple area-based sorting
            self.frames.sort(key=lambda f: f.area, reverse=True)
        elif settings.optimization_level <= 6:
            # Height-based sorting for better packing
            self.frames.sort(key=lambda f: f.height, reverse=True)
        else:
            # Advanced sorting: area, then height, then width
            self.frames.sort(key=lambda f: (f.area, f.height, f.width), reverse=True)
    
    def _calculate_atlas_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Calculate optimal atlas dimensions."""
        if settings.optimization_level == 0:
            # No optimization - use simple grid calculation
            return self._calculate_grid_size(settings)
        
        # Calculate total area needed
        total_area = sum(f.area for f in self.frames)
        padding_area = len(self.frames) * (settings.padding * 2) ** 2
        required_area = int((total_area + padding_area) * settings.efficiency_factor)
        
        # Find smallest power-of-2 size that can fit the content
        size = settings.min_size
        while size * size < required_area and size < settings.max_size:
            size *= 2 if settings.power_of_2 else int(size * 1.5)
        
        return size, size
    
    def _calculate_grid_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Calculate size for simple grid packing (level 0)."""
        if not self.frames:
            return settings.min_size, settings.min_size
        
        # Simple grid arrangement
        frame_count = len(self.frames)
        grid_size = int(np.ceil(np.sqrt(frame_count)))
        
        max_width = max(f.width for f in self.frames)
        max_height = max(f.height for f in self.frames)
        
        width = grid_size * (max_width + settings.padding * 2)
        height = grid_size * (max_height + settings.padding * 2)
        
        if settings.power_of_2:
            width = self._next_power_of_2(width)
            height = self._next_power_of_2(height)
        
        return min(width, settings.max_size), min(height, settings.max_size)
    
    def _pack_frames(self, atlas_width: int, atlas_height: int, settings: AtlasSettings) -> bool:
        """Pack frames into the atlas using the selected algorithm."""
        if settings.algorithm == PackingAlgorithm.NONE:
            return self._pack_grid(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.BOTTOM_LEFT:
            return self._pack_bottom_left(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.BEST_FIT:
            return self._pack_best_fit(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.SKYLINE:
            return self._pack_skyline(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.MAXRECTS:
            return self._pack_maxrects(atlas_width, atlas_height, settings)
        else:
            return self._pack_bottom_left(atlas_width, atlas_height, settings)
    
    def _pack_grid(self, atlas_width: int, atlas_height: int, settings: AtlasSettings) -> bool:
        """Simple grid packing - no optimization."""
        grid_size = int(np.ceil(np.sqrt(len(self.frames))))
        max_width = max(f.width for f in self.frames) if self.frames else 0
        max_height = max(f.height for f in self.frames) if self.frames else 0
        
        cell_width = max_width + settings.padding * 2
        cell_height = max_height + settings.padding * 2
        
        for i, frame in enumerate(self.frames):
            row = i // grid_size
            col = i % grid_size
            
            x = col * cell_width + settings.padding
            y = row * cell_height + settings.padding
            
            if x + frame.width > atlas_width or y + frame.height > atlas_height:
                return False
            
            frame.x = x
            frame.y = y
        
        return True
    
    def _pack_bottom_left(self, atlas_width: int, atlas_height: int, settings: AtlasSettings) -> bool:
        """Bottom-left fill packing algorithm."""
        self.used_rectangles = []
        
        for frame in self.frames:
            packed = False
            
            # Try to find a position for this frame
            for y in range(0, atlas_height - frame.height + 1, settings.padding + 1):
                for x in range(0, atlas_width - frame.width + 1, settings.padding + 1):
                    rect = Rectangle(x, y, frame.width + settings.padding * 2, 
                                   frame.height + settings.padding * 2)
                    
                    if not any(rect.intersects(used) for used in self.used_rectangles):
                        frame.x = x + settings.padding
                        frame.y = y + settings.padding
                        self.used_rectangles.append(rect)
                        packed = True
                        break
                
                if packed:
                    break
            
            if not packed:
                return False
        
        return True
    
    def _pack_best_fit(self, atlas_width: int, atlas_height: int, settings: AtlasSettings) -> bool:
        """Best-fit packing algorithm."""
        self.used_rectangles = []
        
        for frame in self.frames:
            best_x, best_y = -1, -1
            best_waste = float('inf')
            
            # Try all possible positions and pick the one with least waste
            for y in range(0, atlas_height - frame.height + 1, max(1, settings.padding)):
                for x in range(0, atlas_width - frame.width + 1, max(1, settings.padding)):
                    rect = Rectangle(x, y, frame.width + settings.padding * 2, 
                                   frame.height + settings.padding * 2)
                    
                    if not any(rect.intersects(used) for used in self.used_rectangles):
                        # Calculate waste (unused area around this position)
                        waste = self._calculate_waste(x, y, frame.width, frame.height, 
                                                    atlas_width, atlas_height)
                        
                        if waste < best_waste:
                            best_waste = waste
                            best_x, best_y = x, y
            
            if best_x == -1:
                return False
            
            frame.x = best_x + settings.padding
            frame.y = best_y + settings.padding
            rect = Rectangle(best_x, best_y, frame.width + settings.padding * 2, 
                           frame.height + settings.padding * 2)
            self.used_rectangles.append(rect)
        
        return True
    
    def _pack_skyline(self, atlas_width: int, atlas_height: int, settings: AtlasSettings) -> bool:
        """Skyline packing algorithm."""
        skyline = [(0, 0, atlas_width)]  # (x, y, width)
        
        for frame in self.frames:
            best_index = -1
            best_y = float('inf')
            best_x = -1
            
            # Find the best position on the skyline
            for i, (x, y, width) in enumerate(skyline):
                if width >= frame.width + settings.padding * 2:
                    if y < best_y or (y == best_y and x < best_x):
                        best_index = i
                        best_y = y
                        best_x = x
            
            if best_index == -1 or best_y + frame.height + settings.padding * 2 > atlas_height:
                return False
            
            # Place the frame
            frame.x = best_x + settings.padding
            frame.y = best_y + settings.padding
            
            # Update skyline
            frame_width = frame.width + settings.padding * 2
            frame_height = frame.height + settings.padding * 2
            
            # Remove or modify the segment we're using
            x, y, width = skyline[best_index]
            skyline[best_index] = (x + frame_width, y, width - frame_width)
            
            # Add new segment for the frame
            skyline.insert(best_index, (x, y + frame_height, frame_width))
            
            # Remove zero-width segments
            skyline = [(x, y, w) for x, y, w in skyline if w > 0]
            
            # Merge adjacent segments at the same height
            skyline.sort()
            merged = []
            for x, y, w in skyline:
                if merged and merged[-1][1] == y and merged[-1][0] + merged[-1][2] == x:
                    merged[-1] = (merged[-1][0], y, merged[-1][2] + w)
                else:
                    merged.append((x, y, w))
            skyline = merged
        
        return True
    
    def _pack_maxrects(self, atlas_width: int, atlas_height: int, settings: AtlasSettings) -> bool:
        """MaxRects packing algorithm - most advanced."""
        self.free_rectangles = [Rectangle(0, 0, atlas_width, atlas_height)]
        self.used_rectangles = []
        
        for frame in self.frames:
            best_rect = None
            best_score = float('inf')
            
            # Try all free rectangles
            for rect in self.free_rectangles:
                if rect.width >= frame.width + settings.padding * 2 and \
                   rect.height >= frame.height + settings.padding * 2:
                    
                    # Calculate score (prefer smaller waste)
                    waste = (rect.width - frame.width - settings.padding * 2) * \
                           (rect.height - frame.height - settings.padding * 2)
                    
                    if waste < best_score:
                        best_score = waste
                        best_rect = rect
            
            if best_rect is None:
                return False
            
            # Place the frame
            frame.x = best_rect.x + settings.padding
            frame.y = best_rect.y + settings.padding
            
            # Create used rectangle
            used_rect = Rectangle(best_rect.x, best_rect.y, 
                                frame.width + settings.padding * 2, 
                                frame.height + settings.padding * 2)
            self.used_rectangles.append(used_rect)
            
            # Split the free rectangle
            self._split_free_rectangle(best_rect, used_rect)
            
            # Remove the used rectangle from free list
            self.free_rectangles.remove(best_rect)
            
            # Prune overlapping rectangles
            self._prune_free_rectangles()
        
        return True
    
    def _split_free_rectangle(self, free_rect: Rectangle, used_rect: Rectangle):
        """Split a free rectangle after placing a frame."""
        # Create up to 4 new rectangles from the split
        
        # Left split
        if used_rect.x > free_rect.x:
            self.free_rectangles.append(Rectangle(
                free_rect.x, free_rect.y, 
                used_rect.x - free_rect.x, free_rect.height
            ))
        
        # Right split
        if used_rect.right < free_rect.right:
            self.free_rectangles.append(Rectangle(
                used_rect.right, free_rect.y,
                free_rect.right - used_rect.right, free_rect.height
            ))
        
        # Top split
        if used_rect.y > free_rect.y:
            self.free_rectangles.append(Rectangle(
                free_rect.x, free_rect.y,
                free_rect.width, used_rect.y - free_rect.y
            ))
        
        # Bottom split
        if used_rect.bottom < free_rect.bottom:
            self.free_rectangles.append(Rectangle(
                free_rect.x, used_rect.bottom,
                free_rect.width, free_rect.bottom - used_rect.bottom
            ))
    
    def _prune_free_rectangles(self):
        """Remove free rectangles that are inside other free rectangles."""
        to_remove = []
        
        for i, rect1 in enumerate(self.free_rectangles):
            for j, rect2 in enumerate(self.free_rectangles):
                if i != j and self._is_contained(rect1, rect2):
                    to_remove.append(rect1)
                    break
        
        for rect in to_remove:
            if rect in self.free_rectangles:
                self.free_rectangles.remove(rect)
    
    def _is_contained(self, rect1: Rectangle, rect2: Rectangle) -> bool:
        """Check if rect1 is completely contained in rect2."""
        return (rect1.x >= rect2.x and rect1.y >= rect2.y and 
                rect1.right <= rect2.right and rect1.bottom <= rect2.bottom)
    
    def _calculate_waste(self, x: int, y: int, width: int, height: int, 
                        atlas_width: int, atlas_height: int) -> float:
        """Calculate waste metric for a position."""
        # Simple waste calculation - can be improved
        right_waste = max(0, atlas_width - (x + width))
        bottom_waste = max(0, atlas_height - (y + height))
        return right_waste + bottom_waste
    
    def _create_atlas_image(self, atlas_width: int, atlas_height: int) -> Image.Image:
        """Create the final atlas image."""
        atlas = Image.new('RGBA', (atlas_width, atlas_height), (0, 0, 0, 0))
        
        for frame in self.frames:
            try:
                with Image.open(frame.image_path) as img:
                    if frame.rotated:
                        img = img.rotate(90, expand=True)
                    atlas.paste(img, (frame.x, frame.y))
            except Exception as e:
                print(f"Error pasting frame {frame.name}: {e}")
                continue
        
        return atlas
    
    def _generate_sparrow_xml(self, output_path: str, atlas_width: int, atlas_height: int) -> str:
        """Generate Sparrow XML format metadata."""
        root = ET.Element('TextureAtlas')
        root.set('imagePath', f"{Path(output_path).name}.png")
        
        for frame in self.frames:
            subtexture = ET.SubElement(root, 'SubTexture')
            subtexture.set('name', frame.name)
            subtexture.set('x', str(frame.x))
            subtexture.set('y', str(frame.y))
            subtexture.set('width', str(frame.width))
            subtexture.set('height', str(frame.height))
            subtexture.set('frameX', '0')
            subtexture.set('frameY', '0')
            subtexture.set('frameWidth', str(frame.width))
            subtexture.set('frameHeight', str(frame.height))
            subtexture.set('flipX', 'false')
            subtexture.set('flipY', 'false')
            subtexture.set('rotated', str(frame.rotated).lower())
        
        # Pretty print XML
        from xml.dom import minidom
        rough_string = ET.tostring(root, encoding='unicode')
        parsed = minidom.parseString(rough_string)
        return parsed.toprettyxml(indent='  ')
    
    def _calculate_efficiency(self, atlas_width: int, atlas_height: int) -> float:
        """Calculate packing efficiency."""
        if not self.frames:
            return 0.0
        
        used_area = sum(f.area for f in self.frames)
        total_area = atlas_width * atlas_height
        return (used_area / total_area) * 100 if total_area > 0 else 0.0
    
    def _next_power_of_2(self, value: int) -> int:
        """Find the next power of 2 greater than or equal to value."""
        return 2 ** int(np.ceil(np.log2(value)))
    
    def _update_progress(self, current: int, total: int, message: str = ""):
        """Update progress callback."""
        if self.progress_callback:
            self.progress_callback(current, total, message)


# Legacy AtlasGenerator class for backward compatibility
class AtlasGenerator(SparrowAtlasGenerator):
    """Backward compatibility wrapper."""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        super().__init__(progress_callback)
        print("Warning: AtlasGenerator is deprecated. Use SparrowAtlasGenerator instead.")
    
    def generate_atlas(self, input_frames: List[str], output_path: str, 
                      atlas_settings: dict) -> dict:
        """Legacy interface - converts to new format."""
        # Convert legacy format to new format
        animation_groups = {"Animation_01": input_frames}
        
        # Convert legacy settings
        settings = AtlasSettings(
            max_size=atlas_settings.get('max_size', 2048),
            min_size=atlas_settings.get('min_size', 128),
            padding=atlas_settings.get('padding', 2),
            power_of_2=atlas_settings.get('power_of_2', True),
            optimization_level=atlas_settings.get('optimization_level', 5),
            efficiency_factor=atlas_settings.get('efficiency_factor', 1.3)
        )
        
        return super().generate_atlas(animation_groups, output_path, settings)