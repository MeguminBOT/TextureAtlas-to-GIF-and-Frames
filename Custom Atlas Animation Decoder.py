import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional

@dataclass
class TransformationPosition:
    x: float
    y: float

@dataclass
class SpriteInfo:
    SN: str
    IN: str
    ST: str
    FF: int
    LP: str
    TRP: TransformationPosition
    M3D: List[float]

@dataclass
class Event:
    SI: SpriteInfo

@dataclass
class Frame:
    I: int
    DU: int
    E: List[Event] = field(default_factory=list)

@dataclass
class Layer:
    LN: str
    FR: List[Frame] = field(default_factory=list)

@dataclass
class Timeline:
    L: List[Layer] = field(default_factory=list)

@dataclass
class Animation:
    N: str
    SN: str
    TL: Timeline

@dataclass
class AnimationData:
    AN: Animation

class AnimationDecoder(json.JSONDecoder):
    def decode(self, s: str):
        data = super().decode(s)
        def dict_to_dataclass(cls, d):
            if isinstance(d, list):
                return [dict_to_dataclass(cls.__args__[0], item) for item in d]
            if isinstance(d, dict):
                fields = {f.name: dict_to_dataclass(f.type, d.get(f.name)) for f in cls.__dataclass_fields__.values()}
                return cls(**fields)
            return d
        return dict_to_dataclass(AnimationData, data)

def parse_animation_json(file_path: str) -> AnimationData:
    with open(file_path, 'r') as file:
        json_data = file.read()
    return json.loads(json_data, cls=AnimationDecoder)

def print_data(obj, indent=0):
    if isinstance(obj, list):
        for item in obj:
            print_data(item, indent + 2)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            print(" " * indent + f"{key}:")
            print_data(value, indent + 2)
    else:
        if hasattr(obj, '__dataclass_fields__'):
            obj_dict = asdict(obj)
            for key, value in obj_dict.items():
                print(" " * indent + f"{key}:")
                print_data(value, indent + 2)
        else:
            print(" " * indent + str(obj))

if __name__ == "__main__":
    animation_data = parse_animation_json('spritemap1anim.json')
    print_data(animation_data)