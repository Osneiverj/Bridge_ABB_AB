MODULE Comm_ABB_AB_Socket

    !========================================================
    !  ABB socket client transport (binary rawbytes)
    !========================================================

    CONST string cServerIp := "10.22.64.20";
    CONST num cServerPort := 3552;

    CONST num cFrameBytes := 128;
    CONST num cLoopDelay := 0.02;
    CONST num cReconnectWait := 0.50;
    CONST num cSocketTimeout := 1.00;
    CONST num cMaxTimeoutCycles := 10;

    VAR socketdev clientSocket;
    VAR bool bSocketCreated := FALSE;
    VAR bool bConnected := FALSE;

    VAR rawbytes txFrame;
    VAR rawbytes rxFrame;

    PROC Comm_Main()

        WHILE TRUE DO

            IF NOT bConnected THEN
                ConnectLoop;
            ENDIF

            IF bConnected THEN
                CommCycle;
            ENDIF

            WaitTime cLoopDelay;

        ENDWHILE

    ENDPROC


    PROC ConnectLoop()

        SocketCloseSafe;

        ERROR
            SocketCloseSafe;
        ENDERROR

        SocketCreate clientSocket;
        bSocketCreated := TRUE;

        SocketConnect clientSocket, cServerIp, cServerPort\Time:=cSocketTimeout;

        bConnected := TRUE;
        CommOK := TRUE;
        CommFault := FALSE;
        CommLastError := 0;
        CommTimeoutCycles := 0;

        RETURN;

    ERROR
        HandleCommError ERRNO;
        RETURN;

    ENDPROC


    PROC CommCycle()

        BuildTxFrame;

        SocketSend clientSocket\RawData:=txFrame\NoOfBytes:=cFrameBytes\Time:=cSocketTimeout;
        SocketReceive clientSocket\RawData:=rxFrame\ReadNoOfBytes:=cFrameBytes\Time:=cSocketTimeout;

        ParseRxFrame;

        CommOK := TRUE;
        CommFault := FALSE;
        CommLastError := 0;
        CommTimeoutCycles := 0;
        NewData := TRUE;

        RETURN;

    ERROR
        NewData := FALSE;
        HandleCommError ERRNO;
        RETURN;

    ENDPROC


    PROC BuildTxFrame()

        VAR num i;
        VAR num pos;

        ClearRawBytes txFrame;
        pos := 1;

        FOR i FROM 1 TO 6 DO
            PackRawBytes VO_Bits{i}, txFrame, pos\DINT;
            pos := pos + 4;
        ENDFOR

        FOR i FROM 1 TO 26 DO
            PackRawBytes VO_Status{i}, txFrame, pos\INT;
            pos := pos + 2;
        ENDFOR

        FOR i FROM 1 TO 26 DO
            PackRawBytes VO_Parameters{i}, txFrame, pos\INT;
            pos := pos + 2;
        ENDFOR

    ENDPROC


    PROC ParseRxFrame()

        VAR num i;
        VAR num pos;
        VAR num tempNum;

        pos := 1;

        FOR i FROM 1 TO 6 DO
            UnPackRawBytes rxFrame, pos, tempNum\DINT;
            VI_Bits{i} := tempNum;
            pos := pos + 4;
        ENDFOR

        FOR i FROM 1 TO 26 DO
            UnPackRawBytes rxFrame, pos, tempNum\INT;
            VI_Status{i} := tempNum;
            pos := pos + 2;
        ENDFOR

        FOR i FROM 1 TO 26 DO
            UnPackRawBytes rxFrame, pos, tempNum\INT;
            VI_Parameters{i} := tempNum;
            pos := pos + 2;
        ENDFOR

    ENDPROC


    PROC HandleCommError(num nError)

        CommOK := FALSE;
        CommLastError := nError;

        IF nError = ERR_SOCK_TIMEOUT THEN
            CommTimeoutCycles := CommTimeoutCycles + 1;
            IF CommTimeoutCycles >= cMaxTimeoutCycles THEN
                CommFault := TRUE;
            ENDIF
        ELSE
            CommFault := TRUE;
        ENDIF

        bConnected := FALSE;
        SocketCloseSafe;
        WaitTime cReconnectWait;

    ENDPROC


    PROC SocketCloseSafe()

        IF bSocketCreated THEN
            SocketClose clientSocket;
        ENDIF

        bSocketCreated := FALSE;
        bConnected := FALSE;

    ERROR
        bSocketCreated := FALSE;
        bConnected := FALSE;
        RETURN;

    ENDPROC

ENDMODULE
