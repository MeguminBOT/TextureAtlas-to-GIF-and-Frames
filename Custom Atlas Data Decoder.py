# atlas_parser.py
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

@dataclass
class Sprite:
    name: str
    x: int
    y: int
    w: int
    h: int
    rotated: bool

@dataclass
class Atlas:
    SPRITES: List[Sprite] = field(default_factory=list)

@dataclass
class Meta:
    app: str
    version: str
    image: str
    format: str
    size: Dict[str, int]
    resolution: str

@dataclass
class AtlasData:
    ATLAS: Atlas
    meta: Meta

class AtlasDecoder(json.JSONDecoder):
    def decode(self, s: str):
        data = super().decode(s)
        def dict_to_dataclass(cls, d):
            if isinstance(d, list):
                if cls == List[Sprite]:
                    return [dict_to_dataclass(Sprite, item['SPRITE']) for item in d]
                return [dict_to_dataclass(cls.__args__[0], item) for item in d]
            if isinstance(d, dict):
                if hasattr(cls, '__origin__') and cls.__origin__ is dict:
                    return {k: dict_to_dataclass(cls.__args__[1], v) for k, v in d.items()}
                fields = {f.name: dict_to_dataclass(f.type, d.get(f.name)) for f in cls.__dataclass_fields__.values()}
                return cls(**fields)
            return d
        return dict_to_dataclass(AtlasData, data)

def parse_atlas_json(file_path: str) -> AtlasData:
    with open(file_path, 'r') as file:
        json_data = file.read()
    return json.loads(json_data, cls=AtlasDecoder)

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
    atlas_data = parse_atlas_json('spritemap1.json')
    print_data(atlas_data)
