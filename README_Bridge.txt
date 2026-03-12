ABB <-> Python <-> PLC Bridge (Binary 128-byte protocol)
=======================================================

Architecture
------------
1) ABB controller is a TCP client.
2) Python bridge is a TCP server for ABB.
3) Python bridge is an EtherNet/IP explicit messaging client to PLC.
4) Bridge cycle order:
   - receive ABB frame (128 bytes)
   - unpack ABB frame
   - write ABB_TO_PLC_IF in PLC
   - read PLC_TO_ABB_IF from PLC
   - pack response frame (128 bytes)
   - send response to ABB

Binary frame layout (both directions)
-------------------------------------
- Bits: DINT[6] => 6 x int32 signed => 24 bytes
- Status: INT[26] => 26 x int16 signed => 52 bytes
- Parameters: INT[26] => 26 x int16 signed => 52 bytes
- Total fixed length: 128 bytes

Python side
-----------
- comm_schema.py centralizes interface definition for:
  - abb_to_plc
  - plc_to_abb
- abb_codec.py uses struct with little-endian fixed format:
  - pack_abb_frame(bits, status, parameters) -> 128 bytes
  - unpack_abb_frame(data) -> {"bits", "status", "parameters"}
- plc_codec.py maps normalized image to/from PLC UDT values.
- bridge_integrado.py enforces recv_exact(sock, 128) and sendall(128 bytes).

PLC side (UDTs)
---------------
- ABB_TO_PLC_IF
  - Bits : DINT[6]
  - Status : INT[26]
  - Parameters : INT[26]
- PLC_TO_ABB_IF
  - Bits : DINT[6]
  - Status : INT[26]
  - Parameters : INT[26]

ABB RAPID side
--------------
Virtual input image (from Python to ABB):
- VI_Bits{6}
- VI_Status{26}
- VI_Parameters{26}

Virtual output image (from ABB to Python):
- VO_Bits{6}
- VO_Status{26}
- VO_Parameters{26}

Transport module uses binary rawbytes only:
- ClearRawBytes
- PackRawBytes
- UnPackRawBytes
- SocketSend
- SocketReceive

No CSV/string framing is used for process data.

Reconnect behavior
------------------
- Python bridge reconnects ABB socket when timeout/disconnect occurs.
- Python bridge reconnects PLC session when PLC access fails.
- RAPID comm task does not stop on timeout/close/error.
- RAPID marks CommOK/CommFault and retries connection from loop.
- VO_* arrays are not reset during reconnect attempts.
