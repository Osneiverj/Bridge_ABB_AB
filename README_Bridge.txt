Files included
==============

Python
------
comm_schema.py
plc_codec.py
abb_codec.py
bridge_integrado.py

RAPID
-----
Comm_ABB_AB_Data.mod
Comm_ABB_AB_Socket.mod

PLC reference
-------------
PLC_UDT_Definitions.txt

Execution order currently implemented in the integrated bridge
-------------------------------------------------------------
1. Receive ABB frame
2. Write ABB image to PLC
3. Read PLC image
4. Send PLC image back to ABB

Important ABB note
------------------
The RAPID side now uses virtual images:
- VI_Bits / VI_Status / VI_Parameters for data coming from PLC
- VO_Bits / VO_Status / VO_Parameters for data going to PLC

The execution task should use VO_* to publish robot state and VI_* to consume controller commands.
