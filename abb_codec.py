"""Binary ABB frame codec (fixed 128-byte frame, little-endian)."""

from __future__ import annotations

import struct
from typing import Sequence

from comm_schema import ABB_FRAME_BYTES, COMM_SCHEMA

_BITS_KEY = "bits"
_STATUS_KEY = "status"
_PARAMETERS_KEY = "parameters"

_BITS_COUNT = COMM_SCHEMA["abb_to_plc"]["bits_dint_count"]
_STATUS_COUNT = COMM_SCHEMA["abb_to_plc"]["sections"][0]["size"]
_PARAMETERS_COUNT = COMM_SCHEMA["abb_to_plc"]["sections"][1]["size"]

_FORMAT = "<" + ("i" * _BITS_COUNT) + ("h" * _STATUS_COUNT) + ("h" * _PARAMETERS_COUNT)
_STRUCT = struct.Struct(_FORMAT)

if _STRUCT.size != ABB_FRAME_BYTES:
    raise RuntimeError(f"Schema/struct mismatch: {_STRUCT.size} != {ABB_FRAME_BYTES}")


def _require_size(values: Sequence[int], expected: int, field_name: str) -> None:
    if len(values) != expected:
        raise ValueError(f"{field_name} length must be {expected}, got {len(values)}")


def pack_abb_frame(bits: Sequence[int], status: Sequence[int], parameters: Sequence[int]) -> bytes:
    """Pack ABB image to exact 128-byte frame."""
    _require_size(bits, _BITS_COUNT, _BITS_KEY)
    _require_size(status, _STATUS_COUNT, _STATUS_KEY)
    _require_size(parameters, _PARAMETERS_COUNT, _PARAMETERS_KEY)

    values = [int(v) for v in bits] + [int(v) for v in status] + [int(v) for v in parameters]
    packed = _STRUCT.pack(*values)
    if len(packed) != ABB_FRAME_BYTES:
        raise RuntimeError(f"Invalid packed frame size: {len(packed)}")
    return packed


def unpack_abb_frame(data: bytes) -> dict:
    """Unpack exact 128-byte ABB frame into schema image dict."""
    if len(data) != ABB_FRAME_BYTES:
        raise ValueError(f"ABB frame must be exactly {ABB_FRAME_BYTES} bytes, got {len(data)}")

    unpacked = _STRUCT.unpack(data)
    idx = 0

    bits = list(unpacked[idx : idx + _BITS_COUNT])
    idx += _BITS_COUNT

    status = list(unpacked[idx : idx + _STATUS_COUNT])
    idx += _STATUS_COUNT

    parameters = list(unpacked[idx : idx + _PARAMETERS_COUNT])

    return {
        _BITS_KEY: bits,
        _STATUS_KEY: status,
        _PARAMETERS_KEY: parameters,
    }
