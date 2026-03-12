"""Central communication schema for ABB <-> Python <-> PLC bridge."""

from __future__ import annotations

from copy import deepcopy

BITS_DINT_COUNT = 6
STATUS_COUNT = 26
PARAMETERS_COUNT = 26

COMM_SCHEMA = {
    "abb_to_plc": {
        "root_tag": "ABB_TO_PLC_IF",
        "bits_dint_count": BITS_DINT_COUNT,
        "sections": [
            {"name": "status", "type": "int_array", "size": STATUS_COUNT},
            {"name": "parameters", "type": "int_array", "size": PARAMETERS_COUNT},
        ],
    },
    "plc_to_abb": {
        "root_tag": "PLC_TO_ABB_IF",
        "bits_dint_count": BITS_DINT_COUNT,
        "sections": [
            {"name": "status", "type": "int_array", "size": STATUS_COUNT},
            {"name": "parameters", "type": "int_array", "size": PARAMETERS_COUNT},
        ],
    },
}


def total_frame_bytes(direction: str = "abb_to_plc") -> int:
    """Return frame size in bytes for a direction defined in the schema."""
    cfg = COMM_SCHEMA[direction]
    bits_bytes = cfg["bits_dint_count"] * 4
    int16_bytes = sum(section["size"] for section in cfg["sections"]) * 2
    return bits_bytes + int16_bytes


ABB_FRAME_BYTES = total_frame_bytes("abb_to_plc")


def empty_image(direction: str) -> dict:
    """Create an empty image according to schema."""
    cfg = COMM_SCHEMA[direction]
    image = {"bits": [0] * cfg["bits_dint_count"]}
    for section in cfg["sections"]:
        image[section["name"]] = [0] * section["size"]
    return image


ABB_TO_PLC_EMPTY = deepcopy(empty_image("abb_to_plc"))
PLC_TO_ABB_EMPTY = deepcopy(empty_image("plc_to_abb"))
