
import json
from typing import List, Union, Optional, Dict, Any
from dataclasses import dataclass

class AnimationData:
	@staticmethod
	def set_field_bool(abstract_obj: Optional[Dict], things: List[str], set_value: Any = None) -> Any:
		if abstract_obj is None:
			return {}
		for thing in things:
			if set_value is not None:
				abstract_obj[thing] = set_value
				return set_value
			if thing in abstract_obj:
				return abstract_obj[thing]
		return {}

class Loop:
	LOOP = "Loop"
	PLAY_ONCE = "PlayOnce"
	SINGLE_FRAME = "SingleFrame"

class SymbolType:
	GRAPHIC = "Graphic"
	MOVIE_CLIP = "MovieClip"
	BUTTON = "Button"

class LayerType:
	NORMAL = "Normal"
	CLIPPER = "Clipper"
	CLIPPED = lambda layer: f"Clipped({layer})"
	FOLDER = "Folder"


class AnimAtlas:
	def __init__(self):
		self._animation = None
		self._symbol_dictionary = None
		self._metadata = None

	@property
	def AN(self) -> Optional[Any]:
		return AnimationData.set_field_bool(self.__dict__, ["AN", "ANIMATION"])

	@property
	def SD(self) -> Optional[Any]:
		return AnimationData.set_field_bool(self.__dict__, ["SD", "SYMBOL_DICTIONARY"])

	@property
	def MD(self) -> Optional[Any]:
		return AnimationData.set_field_bool(self.__dict__, ["MD", "metadata"])

class SymbolDictionary:
	def __init__(self):
		self.symbols = []

	@property
	def S(self) -> List[Any]:
		return AnimationData.set_field_bool(self.__dict__, ["S", "Symbols"])

class Animation:
	def __init__(self):
		self._symbol_name = ""
		self._name = ""
		self._timeline = None
		self._stage_instance = None

	@property
	def SN(self) -> str:
		return AnimationData.set_field_bool(self.__dict__, ["SN", "SYMBOL_name"])

	@property
	def N(self) -> str:
		return AnimationData.set_field_bool(self.__dict__, ["N", "name"])

	@property
	def TL(self) -> Optional[Any]:
		return AnimationData.set_field_bool(self.__dict__, ["TL", "TIMELINE"])

	@property
	def STI(self) -> Optional[Any]:
		return AnimationData.set_field_bool(self.__dict__, ["STI", "StageInstance"])

class StageInstance:
	@property
	def SI(self) -> Optional[Any]:
		return AnimationData.set_field_bool(self.__dict__, ["SI", "SYMBOL_Instance"])

class SymbolData:
	@property
	def SN(self) -> str:
		return AnimationData.set_field_bool(self.__dict__, ["SN", "SYMBOL_name"])

	@property
	def TL(self) -> Optional[Any]:
		return AnimationData.set_field_bool(self.__dict__, ["TL", "TIMELINE"])

class Timeline:
	def __init__(self):
		self.layers = []

	@property
	def L(self) -> List[Any]:
		return AnimationData.set_field_bool(self.__dict__, ["L", "LAYERS"])

	@L.setter
	def L(self, value: List[Any]):
		AnimationData.set_field_bool(self.__dict__, ["L", "LAYERS"], value)

class Layers:
	def __init__(self):
		self.layer_name = ""
		self.layer_type = ""
		self.clipped_by = ""
		self.frames = []

	@property
	def LN(self) -> str:
		return AnimationData.set_field_bool(self.__dict__, ["LN", "Layer_name"])

	@property
	def LT(self) -> str:
		return AnimationData.set_field_bool(self.__dict__, ["LT", "Layer_type"])

	@property
	def Clpb(self) -> str:
		return AnimationData.set_field_bool(self.__dict__, ["Clpb", "Clipped_by"])

	@property
	def FR(self) -> List[Any]:
		return AnimationData.set_field_bool(self.__dict__, ["FR", "Frames"])

	@FR.setter
	def FR(self, value: List[Any]):
		AnimationData.set_field_bool(self.__dict__, ["FR", "Frames"], value)

class MetaData:
	@property
	def FRT(self) -> float:
		return AnimationData.set_field_bool(self.__dict__, ["FRT", "framerate"])

class Frame:
	def __init__(self):
		self.name = ""
		self.index = 0
		self.duration = 0
		self.elements = []

	@property
	def N(self) -> str:
		return AnimationData.set_field_bool(self.__dict__, ["N", "name"])

	@property
	def I(self) -> int:
		return AnimationData.set_field_bool(self.__dict__, ["I", "index"])

	@property
	def DU(self) -> int:
		return AnimationData.set_field_bool(self.__dict__, ["DU", "duration"])

	@property
	def E(self) -> List[Any]:
		return AnimationData.set_field_bool(self.__dict__, ["E", "elements"])

class Bitmap:
	@property
	def N(self) -> str:
		return AnimationData.set_field_bool(self.__dict__, ["N", "name"])

	@property
	def POS(self) -> Optional[Dict[str, float]]:
		return AnimationData.set_field_bool(self.__dict__, ["POS", "Position"])

class AtlasSymbolInstance(Bitmap):
	@property
	def M3D(self) -> Union[List[float], Dict[str, float]]:
		return AnimationData.set_field_bool(self.__dict__, ["M3D", "Matrix3D"])

# Represents a 4x4 matrix used for transformations in 3D space.
@dataclass
class Matrix3D:
	m00:float
	m01:float
	m02:float
	m03:float
	m10:float
	m11:float
	m12:float
	m13:float
	m20:float
	m21:float
	m22:float
	m23:float
	m30:float
	m31:float
	m32:float
	m33:float

# Represents a 2D point used for transformations (positioning).
@dataclass
class TransformationPoint:
	x:float
	y:float
