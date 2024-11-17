import json
from typing import Dict, List

class SpriteFrame:
    def __init__(self, name: str, x: int, y: int, width: int, height: int, rotated: bool = False):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rotated = rotated

    def __repr__(self):
        return f"<SpriteFrame {self.name} ({self.x},{self.y},{self.width}x{self.height}, rotated={self.rotated})>"

class SpriteMap:
    def __init__(self, atlas_path: str):
        self.atlas_path = atlas_path
        self.frames: List[SpriteFrame] = []

    def load_from_json(self, json_path: str):
        with open(json_path, 'r') as file:
            data = json.load(file)

        for frame_name, frame_data in data['frames'].items():
            frame = SpriteFrame(
                name=frame_name,
                x=frame_data['frame']['x'],
                y=frame_data['frame']['y'],
                width=frame_data['frame']['w'],
                height=frame_data['frame']['h'],
                rotated=frame_data.get('rotated', False)
            )
            self.frames.append(frame)

    def find_frame(self, name: str) -> SpriteFrame:
        for frame in self.frames:
            if frame.name == name:
                return frame
        raise ValueError(f"Frame '{name}' not found.")

    def __repr__(self):
        return f"<SpriteMap with {len(self.frames)} frames>"