"""Integrated ABB <-> PC <-> PLC bridge.
"""

import socket
import time
from collections import deque
from typing import Optional

from pycomm3 import LogixDriver

from abb_codec import AbbCodec, FrameBuffer
from comm_schema import WATCHDOG_INDEX, WATCHDOG_SECTION
from plc_codec import (
    build_member_read_list,
    build_member_write_list,
    make_empty_image,
    parse_read_results,
)

# ============================================================
# Configuration
# ============================================================

ABB_HOST = "0.0.0.0"
ABB_PORT = 3552
ABB_RECV_BUFFER = 4096
ABB_SOCKET_TIMEOUT = 2.0

PLC_IP = "10.22.64.10"
PLC_RECONNECT_DELAY = 1.0

MAIN_LOOP_DELAY = 0.05
STATUS_REFRESH_DELAY = 0.10
MAX_EVENTS = 12
DISPLAY_BITS = 20
DISPLAY_INTS = 26

# ============================================================
# Bridge state
# ============================================================

codec = AbbCodec(rx_direction="robot_to_plc", tx_direction="plc_to_robot")
rx_buffer = FrameBuffer()

robot_to_plc = make_empty_image("robot_to_plc")
plc_to_robot = make_empty_image("plc_to_robot")

abb_connected = False
plc_connected = False
last_error = "None"
cycle_counter = 0
last_status_render = 0.0
last_plc_write_ok = 0.0
last_plc_read_ok = 0.0

abb_rx_frames = 0
abb_tx_frames = 0

# Event panel
events = deque(maxlen=MAX_EVENTS)


# ============================================================
# Utility functions
# ============================================================

def add_event(message: str):
    timestamp = time.strftime("%H:%M:%S")
    events.appendleft(f"{timestamp} | {message}")


def get_bit(word: int, bit: int) -> bool:
    return ((word >> bit) & 1) == 1


def get_packed_bit(words, bit_index: int) -> int:
    if bit_index < 32:
        word_index = 0
        local_bit = bit_index
    elif bit_index < 64:
        word_index = 1
        local_bit = bit_index - 32
    elif bit_index < 96:
        word_index = 2
        local_bit = bit_index - 64
    elif bit_index < 128:
        word_index = 3
        local_bit = bit_index - 96
    elif bit_index < 160:
        word_index = 4
        local_bit = bit_index - 128
    else:
        word_index = 5
        local_bit = bit_index - 160

    return 1 if get_bit(int(words[word_index]), local_bit) else 0


def build_bit_list(words, count: int = DISPLAY_BITS):
    return [get_packed_bit(words, i) for i in range(count)]


def format_bits(words, title: str) -> str:
    bits = build_bit_list(words, DISPLAY_BITS)
    items = [f"{i:02d}:{bits[i]}" for i in range(len(bits))]
    return f"{title:<22} " + " ".join(items)


def format_section(section_values, title: str) -> str:
    first = " ".join([f"{i+1:02d}:{int(section_values[i])}" for i in range(min(13, len(section_values)))])
    second = " ".join([f"{i+14:02d}:{int(section_values[i+13])}" for i in range(min(13, max(0, len(section_values)-13)))])

    line1 = f"{title:<22} {first}"
    line2 = f"{'':<22} {second}"
    return line1 + ("\n" + line2 if second else "")


def current_watchdog_info() -> str:
    rob_wd = int(robot_to_plc[WATCHDOG_SECTION][WATCHDOG_INDEX])
    plc_wd = int(plc_to_robot[WATCHDOG_SECTION][WATCHDOG_INDEX])
    return f"Robot WD: {rob_wd}   PLC WD: {plc_wd}"


def render_status(force: bool = False):
    global last_status_render

    now = time.time()
    if (not force) and (now - last_status_render < STATUS_REFRESH_DELAY):
        return

    last_status_render = now

    status_lines = []
    status_lines.append("\033[2J\033[H")
    status_lines.append("=" * 170)
    status_lines.append(" ABB <-> PC <-> PLC BRIDGE STATUS ".center(170, "="))
    status_lines.append("=" * 170)
    status_lines.append(
        f"ABB Connected: {'YES' if abb_connected else 'NO ':<3}   "
        f"PLC Connected: {'YES' if plc_connected else 'NO ':<3}   "
        f"Cycle: {cycle_counter:<8}   "
        f"ABB RX/TX Frames: {abb_rx_frames}/{abb_tx_frames}"
    )
    status_lines.append(
        f"{current_watchdog_info()}   "
        f"Last PLC Write OK: {last_plc_write_ok:.3f}   Last PLC Read OK: {last_plc_read_ok:.3f}"
    )
    status_lines.append(f"Last Error: {last_error}")
    status_lines.append("-" * 170)

    status_lines.append(format_bits(robot_to_plc["Bits"], "ABB -> PLC Bits"))
    status_lines.append(format_bits(plc_to_robot["Bits"], "PLC -> ABB Bits"))
    status_lines.append("-" * 170)

    status_lines.append(format_section(robot_to_plc["Status"], "ABB -> PLC Status"))
    status_lines.append("")
    status_lines.append(format_section(robot_to_plc["Parameters"], "ABB -> PLC Parameters"))
    status_lines.append("-" * 170)
    status_lines.append(format_section(plc_to_robot["Status"], "PLC -> ABB Status"))
    status_lines.append("")
    status_lines.append(format_section(plc_to_robot["Parameters"], "PLC -> ABB Parameters"))
    status_lines.append("-" * 170)

    status_lines.append("Recent Events")
    if events:
        for event in list(events)[:8]:
            status_lines.append(f"  {event}")
    else:
        status_lines.append("  No events yet")

    print("\n".join(status_lines), end="", flush=True)


# ============================================================
# PLC functions
# ============================================================

def plc_open() -> Optional[LogixDriver]:
    global plc_connected, last_error

    try:
        plc = LogixDriver(PLC_IP)
        plc.open()

        if plc.connected:
            plc_connected = True
            last_error = "None"
            add_event(f"PLC connected to {PLC_IP}")
            return plc

        plc_connected = False
        last_error = "PLC open failed"
        add_event("PLC open failed")
        return None

    except Exception as exc:
        plc_connected = False
        last_error = f"PLC connection error: {exc}"
        add_event(last_error)
        return None


def plc_close(plc: Optional[LogixDriver]):
    global plc_connected

    if plc is None:
        plc_connected = False
        return

    try:
        plc.close()
    except Exception:
        pass

    plc_connected = False


def plc_write_from_robot(plc: LogixDriver):
    global last_plc_write_ok

    items = build_member_write_list("robot_to_plc", robot_to_plc)
    plc.write(*items)
    last_plc_write_ok = time.time()


def plc_read_to_robot(plc: LogixDriver):
    global plc_to_robot, last_plc_read_ok

    tags = build_member_read_list("plc_to_robot")
    results = plc.read(*tags)
    plc_to_robot = parse_read_results("plc_to_robot", results)
    last_plc_read_ok = time.time()


# ============================================================
# ABB server functions
# ============================================================

def abb_server_create() -> socket.socket:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((ABB_HOST, ABB_PORT))
    server.listen(1)
    add_event(f"ABB server listening on {ABB_HOST}:{ABB_PORT}")
    return server


def abb_wait_connection(server: socket.socket):
    global abb_connected, last_error

    add_event("Waiting for ABB connection")
    conn, addr = server.accept()
    conn.settimeout(ABB_SOCKET_TIMEOUT)
    abb_connected = True
    last_error = "None"
    rx_buffer.buffer = ""
    add_event(f"ABB connected from {addr}")
    return conn, addr


def abb_close_connection(conn: Optional[socket.socket]):
    global abb_connected

    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass

    abb_connected = False


def abb_receive_image(conn: socket.socket) -> bool:
    """Receive at most one ABB frame and update robot_to_plc image.

    Returns True only when one complete valid frame was received.
    """
    global robot_to_plc, abb_rx_frames

    data = conn.recv(ABB_RECV_BUFFER)
    if not data:
        raise ConnectionResetError("ABB disconnected")

    rx_buffer.append(data.decode(errors="ignore"))
    payload = rx_buffer.pop_frame()
    if payload is None:
        return False

    image = codec.decode_payload(payload)
    robot_to_plc = image
    abb_rx_frames += 1
    return True


def abb_send_image(conn: socket.socket):
    global abb_tx_frames

    payload = codec.encode_payload(plc_to_robot)
    conn.sendall(payload.encode())
    abb_tx_frames += 1


# ============================================================
# Main bridge
# ============================================================

def main():
    global last_error, cycle_counter

    plc = None
    server = None
    abb_conn = None

    try:
        server = abb_server_create()
        render_status(force=True)

        while True:
            if plc is None or not plc_connected:
                plc_close(plc)
                plc = plc_open()
                render_status(force=True)

                if plc is None:
                    time.sleep(PLC_RECONNECT_DELAY)
                    render_status()
                    continue

            if abb_conn is None or not abb_connected:
                try:
                    abb_conn, _ = abb_wait_connection(server)
                    render_status(force=True)
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    last_error = f"ABB accept error: {exc}"
                    add_event(last_error)
                    abb_close_connection(abb_conn)
                    abb_conn = None
                    time.sleep(1.0)
                    render_status()
                    continue

            try:
                received = abb_receive_image(abb_conn)
                if not received:
                    time.sleep(MAIN_LOOP_DELAY)
                    render_status()
                    continue

                # Agreed sequence:
                # 1) Receive ABB
                # 2) Write ABB -> PLC
                # 3) Read PLC -> ABB
                # 4) Respond ABB
                plc_write_from_robot(plc)
                plc_read_to_robot(plc)
                abb_send_image(abb_conn)

                cycle_counter += 1
                last_error = "None"
                render_status()
                time.sleep(MAIN_LOOP_DELAY)

            except socket.timeout:
                last_error = "ABB socket timeout"
                add_event(last_error)
                abb_close_connection(abb_conn)
                abb_conn = None
                time.sleep(0.2)
                render_status(force=True)

            except (ConnectionResetError, BrokenPipeError) as exc:
                last_error = f"ABB connection lost: {exc}"
                add_event(last_error)
                abb_close_connection(abb_conn)
                abb_conn = None
                time.sleep(0.2)
                render_status(force=True)

            except KeyboardInterrupt:
                raise

            except Exception as exc:
                last_error = f"Bridge cycle error: {exc}"
                add_event(last_error)
                plc_close(plc)
                plc = None
                time.sleep(0.5)
                render_status(force=True)

    except KeyboardInterrupt:
        add_event("Bridge stopped by user")
        render_status(force=True)
        print()

    finally:
        abb_close_connection(abb_conn)
        plc_close(plc)

        if server is not None:
            try:
                server.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
