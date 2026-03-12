"""PLC codec using UDT-oriented access mapped by central schema."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from comm_schema import COMM_SCHEMA, empty_image


def make_empty_image(direction: str) -> dict:
    return deepcopy(empty_image(direction))


def _cfg(direction: str) -> dict:
    return COMM_SCHEMA[direction]


def validate_image(direction: str, image: dict) -> None:
    cfg = _cfg(direction)

    bits = image.get("bits", [])
    if len(bits) != cfg["bits_dint_count"]:
        raise ValueError(f"bits length mismatch for {direction}")

    for section in cfg["sections"]:
        key = section["name"]
        values = image.get(key, [])
        if len(values) != section["size"]:
            raise ValueError(f"{key} length mismatch for {direction}")


def _extract_tag_value(tag_result: Any) -> Any:
    if hasattr(tag_result, "value"):
        return tag_result.value
    return tag_result


def parse_udt_value(direction: str, udt_value: dict) -> dict:
    """Convert PLC UDT dict value to normalized image: bits/status/parameters."""
    cfg = _cfg(direction)
    image = make_empty_image(direction)

    bits = udt_value.get("Bits")
    if bits is None:
        bits = udt_value.get("bits")
    if bits is None:
        raise ValueError("UDT value missing Bits")
    image["bits"] = [int(v) for v in bits]

    for section in cfg["sections"]:
        key = section["name"]
        plc_key = key.capitalize()
        values = udt_value.get(plc_key)
        if values is None:
            values = udt_value.get(key)
        if values is None:
            raise ValueError(f"UDT value missing {plc_key}")
        image[key] = [int(v) for v in values]

    validate_image(direction, image)
    return image


def parse_read_result(direction: str, read_result: Any) -> dict:
    """Parse pycomm3 Tag result (or direct dict) from root UDT read."""
    value = _extract_tag_value(read_result)
    if not isinstance(value, dict):
        raise ValueError("Expected PLC UDT dict value")
    return parse_udt_value(direction, value)


def image_to_udt_payload(direction: str, image: dict) -> dict:
    """Convert normalized image to payload that can be written to UDT root tag."""
    validate_image(direction, image)
    payload = {"Bits": [int(v) for v in image["bits"]]}
    for section in _cfg(direction)["sections"]:
        key = section["name"]
        payload[key.capitalize()] = [int(v) for v in image[key]]
    return payload
