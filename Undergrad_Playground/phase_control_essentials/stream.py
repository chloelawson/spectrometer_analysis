# phase_control/io/models.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(slots=True)
class StreamMeta:
    """
    Static information about the spectrometer stream.

    This is sent once as the initial 'meta' JSON object by the
    32-bit acquisition process.
    """
    device_index: int
    num_pixels: int
    wavelengths: Optional[List[float]]  # may be None if not available


@dataclass(slots=True)
class StreamFrame:
    """
    One spectrum frame from the acquisition process.

    Corresponds to a 'frame' JSON object.
    """
    timestamp: str
    device_index: int
    counts: List[int]
