"""ABB socket framing and schema-based telegram encode/decode.
"""

from copy import deepcopy
from typing import List, Tuple

from comm_schema import ABB_FRAME_START, ABB_FRAME_END, COMM_SCHEMA, make_empty_direction


class FrameBuffer:
    """Simple stream buffer using start/end delimiters."""

    def __init__(self, start_marker: str = ABB_FRAME_START, end_marker: str = ABB_FRAME_END):
        self.start_marker = start_marker
        self.end_marker = end_marker
        self.buffer = ""

    def append(self, text: str) -> None:
        self.buffer += text

    def pop_frame(self) -> str | None:
        """Return one complete frame payload without delimiters."""
        start = self.buffer.find(self.start_marker)
        if start < 0:
            # Drop garbage if no start marker exists.
            if len(self.buffer) > 2048:
                self.buffer = ""
            return None

        end = self.buffer.find(self.end_marker, start + 1)
        if end < 0:
            # Keep only from start marker forward.
            if start > 0:
                self.buffer = self.buffer[start:]
            return None

        payload = self.buffer[start + 1:end]
        self.buffer = self.buffer[end + 1:]
        return payload


class AbbCodec:
    """Encode and decode ABB telegrams based on the central schema."""

    def __init__(self, rx_direction: str, tx_direction: str):
        self.rx_direction = rx_direction
        self.tx_direction = tx_direction
        self.rx_cfg = COMM_SCHEMA[rx_direction]
        self.tx_cfg = COMM_SCHEMA[tx_direction]
        self.expected_rx_fields = self._field_count(self.rx_cfg)

    @staticmethod
    def _field_count(cfg: dict) -> int:
        return cfg["digital_dints"] + sum(section["size"] for section in cfg["sections"])

    def empty_rx_image(self) -> dict:
        return deepcopy(make_empty_direction(self.rx_direction))

    def empty_tx_image(self) -> dict:
        return deepcopy(make_empty_direction(self.tx_direction))

    def decode_payload(self, payload: str) -> dict:
        parts = [part.strip() for part in payload.split(",") if part.strip() != ""]
        if len(parts) != self.expected_rx_fields:
            raise ValueError(f"Invalid ABB payload field count: {len(parts)} expected {self.expected_rx_fields}")

        image = self.empty_rx_image()
        idx = 0

        for i in range(self.rx_cfg["digital_dints"]):
            image["Bits"][i] = int(parts[idx])
            idx += 1

        for section in self.rx_cfg["sections"]:
            sec_name = section["name"]
            for i in range(section["size"]):
                image[sec_name][i] = int(parts[idx])
                idx += 1

        return image

    def encode_payload(self, image: dict) -> str:
        fields: List[str] = []

        for value in image["Bits"]:
            fields.append(str(int(value)))

        for section in self.tx_cfg["sections"]:
            sec_name = section["name"]
            for value in image[sec_name]:
                fields.append(str(int(value)))

        return ABB_FRAME_START + ",".join(fields) + ABB_FRAME_END
