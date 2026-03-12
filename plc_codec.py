"""PLC codec helpers for generic schema-based Logix access.
"""

from copy import deepcopy
from typing import Dict, List, Tuple

from comm_schema import COMM_SCHEMA, make_empty_direction


def make_empty_image(direction: str) -> dict:
    """Return a fresh image for the selected direction."""
    return deepcopy(make_empty_direction(direction))


def _direction_cfg(direction: str) -> dict:
    return COMM_SCHEMA[direction]


def build_member_tag_list(direction: str) -> List[str]:
    """Build a flat member tag list for reads based on the schema."""
    cfg = _direction_cfg(direction)
    root = cfg["root_tag"]

    tags: List[str] = []

    for i in range(cfg["digital_dints"]):
        tags.append(f"{root}.Bits[{i}]")

    for section in cfg["sections"]:
        sec_name = section["name"]
        for i in range(section["size"]):
            tags.append(f"{root}.{sec_name}[{i}]")

    return tags

def build_member_read_list(direction: str) -> List[str]:
    """Alias kept for readability in the bridge main loop."""
    return build_member_tag_list(direction)


def build_member_write_list(direction: str, image: Dict[str, List[int]]) -> List[Tuple[str, int]]:
    """Build a flat write list for plc.write(*items)."""
    cfg = _direction_cfg(direction)
    root = cfg["root_tag"]

    items: List[Tuple[str, int]] = []

    for i in range(cfg["digital_dints"]):
        items.append((f"{root}.Bits[{i}]", int(image["Bits"][i])))

    for section in cfg["sections"]:
        sec_name = section["name"]
        values = image[sec_name]
        for i in range(section["size"]):
            items.append((f"{root}.{sec_name}[{i}]", int(values[i])))

    return items


def parse_read_results(direction: str, results) -> Dict[str, List[int]]:
    """Convert plc.read() flat results into a structured image."""
    cfg = _direction_cfg(direction)
    image = make_empty_image(direction)

    expected = cfg["digital_dints"] + sum(section["size"] for section in cfg["sections"])
    if not isinstance(results, list):
        raise RuntimeError("Unexpected PLC read result type")
    if len(results) != expected:
        raise RuntimeError(f"Unexpected PLC read result length: {len(results)} expected {expected}")

    idx = 0

    for i in range(cfg["digital_dints"]):
        image["Bits"][i] = int(results[idx].value)
        idx += 1

    for section in cfg["sections"]:
        sec_name = section["name"]
        for i in range(section["size"]):
            image[sec_name][i] = int(results[idx].value)
            idx += 1

    return image
