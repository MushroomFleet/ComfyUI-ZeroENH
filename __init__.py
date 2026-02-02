"""
ComfyUI-ZeroENH: Deterministic Prompt Enhancement via Procedural Augmentation

This custom node pack provides deterministic prompt enhancement using the ZeroBytes
position-is-seed methodology. Same inputs always produce identical outputs.

https://github.com/MushroomFleet/ComfyUI-ZeroENH
"""

from .nodes.DJZ_ZeroENH_V1 import NODE_CLASS_MAPPINGS as V1_MAPPINGS
from .nodes.DJZ_ZeroENH_V1 import NODE_DISPLAY_NAME_MAPPINGS as V1_DISPLAY_MAPPINGS
from .nodes.DJZ_ZeroENH_V2 import NODE_CLASS_MAPPINGS as V2_MAPPINGS
from .nodes.DJZ_ZeroENH_V2 import NODE_DISPLAY_NAME_MAPPINGS as V2_DISPLAY_MAPPINGS

# Merge all node mappings
NODE_CLASS_MAPPINGS = {**V1_MAPPINGS, **V2_MAPPINGS}
NODE_DISPLAY_NAME_MAPPINGS = {**V1_DISPLAY_MAPPINGS, **V2_DISPLAY_MAPPINGS}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

WEB_DIRECTORY = "./web"

__version__ = "1.0.0"
