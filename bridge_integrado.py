"""Integrated ABB (TCP server) <-> Python <-> PLC (EtherNet/IP explicit) bridge.

Cycle order:
1) Receive 128 bytes from ABB
2) Unpack ABB frame
3) Write ABB image to PLC
4) Read PLC image
5) Pack PLC image to 128 bytes
6) Reply to ABB
"""

from __future__ import annotations

import socket
import time
from typing import Optional

from pycomm3 import LogixDriver

from abb_codec import pack_abb_frame, unpack_abb_frame
from comm_schema import ABB_FRAME_BYTES, COMM_SCHEMA
from plc_codec import image_to_udt_payload, make_empty_image, parse_read_result

ABB_HOST = "0.0.0.0"
ABB_PORT = 3552
ABB_ACCEPT_TIMEOUT_S = 1.0
ABB_RECV_TIMEOUT_S = 3.0

PLC_IP = "10.22.64.10"
PLC_RECONNECT_DELAY_S = 1.0
ABB_RECONNECT_DELAY_S = 0.4
IDLE_DELAY_S = 0.01

ABB_TO_PLC_TAG = COMM_SCHEMA["abb_to_plc"]["root_tag"]
PLC_TO_ABB_TAG = COMM_SCHEMA["plc_to_abb"]["root_tag"]


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def recv_exact(sock: socket.socket, size: int) -> bytes:
    """Receive exactly size bytes or raise on timeout/disconnect."""
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionResetError("socket closed by peer")
        data.extend(chunk)
    return bytes(data)


def open_plc() -> Optional[LogixDriver]:
    try:
        plc = LogixDriver(PLC_IP)
        plc.open()
        if plc.connected:
            log(f"PLC connected: {PLC_IP}")
            return plc
        log("PLC open failed")
    except Exception as exc:
        log(f"PLC connect error: {exc}")
    return None


def close_plc(plc: Optional[LogixDriver]) -> None:
    if plc is None:
        return
    try:
        plc.close()
    except Exception:
        pass


def write_abb_to_plc(plc: LogixDriver, abb_image: dict) -> None:
    payload = image_to_udt_payload("abb_to_plc", abb_image)
    result = plc.write((ABB_TO_PLC_TAG, payload))
    if hasattr(result, "error") and result.error:
        raise RuntimeError(f"PLC write error: {result.error}")


def read_plc_to_abb(plc: LogixDriver) -> dict:
    result = plc.read(PLC_TO_ABB_TAG)
    if hasattr(result, "error") and result.error:
        raise RuntimeError(f"PLC read error: {result.error}")
    return parse_read_result("plc_to_abb", result)


def open_server() -> socket.socket:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((ABB_HOST, ABB_PORT))
    server.listen(1)
    server.settimeout(ABB_ACCEPT_TIMEOUT_S)
    log(f"ABB server listening on {ABB_HOST}:{ABB_PORT}")
    return server


def accept_abb(server: socket.socket) -> Optional[socket.socket]:
    try:
        conn, addr = server.accept()
        conn.settimeout(ABB_RECV_TIMEOUT_S)
        log(f"ABB connected from {addr[0]}:{addr[1]}")
        return conn
    except socket.timeout:
        return None


def close_abb(conn: Optional[socket.socket]) -> None:
    if conn is None:
        return
    try:
        conn.close()
    except Exception:
        pass


def main() -> None:
    plc = None
    server = None
    abb_conn = None

    abb_to_plc_image = make_empty_image("abb_to_plc")
    plc_to_abb_image = make_empty_image("plc_to_abb")

    try:
        server = open_server()

        while True:
            if plc is None:
                plc = open_plc()
                if plc is None:
                    time.sleep(PLC_RECONNECT_DELAY_S)
                    continue

            if abb_conn is None:
                abb_conn = accept_abb(server)
                if abb_conn is None:
                    time.sleep(IDLE_DELAY_S)
                    continue

            try:
                rx_data = recv_exact(abb_conn, ABB_FRAME_BYTES)
                abb_to_plc_image = unpack_abb_frame(rx_data)

                write_abb_to_plc(plc, abb_to_plc_image)
                plc_to_abb_image = read_plc_to_abb(plc)

                tx_data = pack_abb_frame(
                    plc_to_abb_image["bits"],
                    plc_to_abb_image["status"],
                    plc_to_abb_image["parameters"],
                )
                abb_conn.sendall(tx_data)

            except socket.timeout:
                log("ABB timeout, reconnecting ABB")
                close_abb(abb_conn)
                abb_conn = None
                time.sleep(ABB_RECONNECT_DELAY_S)

            except (ConnectionResetError, BrokenPipeError) as exc:
                log(f"ABB disconnected: {exc}")
                close_abb(abb_conn)
                abb_conn = None
                time.sleep(ABB_RECONNECT_DELAY_S)

            except Exception as exc:
                log(f"Bridge cycle error: {exc}")
                close_abb(abb_conn)
                abb_conn = None
                close_plc(plc)
                plc = None
                time.sleep(PLC_RECONNECT_DELAY_S)

    except KeyboardInterrupt:
        log("Bridge stopped by user")

    finally:
        close_abb(abb_conn)
        close_plc(plc)
        if server is not None:
            try:
                server.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
