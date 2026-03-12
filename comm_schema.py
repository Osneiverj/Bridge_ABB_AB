"""Communication schema shared by the bridge codecs.
"""

ABB_FRAME_START = "|"
ABB_FRAME_END = "|"

COMM_SCHEMA = {
    "plc_to_robot": {
        "root_tag": "PLC_TO_ROBOT_IF",
        "digital_dints": 6,
        "sections": [
            {"name": "Status", "size": 26, "type": "INT"},
            {"name": "Parameters", "size": 26, "type": "INT"},
        ],
    },
    "robot_to_plc": {
        "root_tag": "ROBOT_TO_PLC_IF",
        "digital_dints": 6,
        "sections": [
            {"name": "Status", "size": 26, "type": "INT"},
            {"name": "Parameters", "size": 26, "type": "INT"},
        ],
    },
}


# Watchdog convention used by the current example table.
# Status[0] is the watchdog word in both directions.
WATCHDOG_SECTION = "Status"
WATCHDOG_INDEX = 0


def make_empty_direction(direction: str) -> dict:
    """Create an empty image dictionary for one communication direction."""
    cfg = COMM_SCHEMA[direction]
    image = {
        "Bits": [0] * cfg["digital_dints"],
    }

    for section in cfg["sections"]:
        image[section["name"]] = [0] * section["size"]

    return image


PLC_TO_ROBOT_EMPTY = make_empty_direction("plc_to_robot")
ROBOT_TO_PLC_EMPTY = make_empty_direction("robot_to_plc")
