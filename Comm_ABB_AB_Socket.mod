MODULE Comm_ABB_AB_Socket

    !========================================================
    !  CONFIGURATION
    !========================================================
    CONST string cRemoteIP := "127.0.0.1";
    CONST num cPort := 3552;

    CONST num cRxTimeout := 1;
    CONST num cReconnectWait := 0.2;
    CONST num cLoopWait := 0.05;
    CONST num cMaxTimeoutCycles := 5;

    CONST string cFrameStart := "|";
    CONST string cFrameEnd := "|";

    !========================================================
    !  SOCKET
    !========================================================
    VAR socketdev socket1;
    VAR socketstatus socketState;
    VAR bool bSocketCreated := FALSE;

    !========================================================
    !  BUFFERS
    !========================================================
    VAR string txPayload := "";
    VAR string txFrame := "";
    VAR string rxFrame := "";
    VAR string rxPayload := "";

    !========================================================
    !  PUBLIC ENTRY POINT
    !========================================================

    PROC main()
        CommRun;
    ENDPROC


    PROC CommRun()

        CommInit;

        WHILE TRUE DO
            CommCycle;
            WaitTime cLoopWait;
        ENDWHILE

    ENDPROC


    PROC CommInit()

        ResetViData;
        ResetCommState;
        CloseSocketSafe;

    ENDPROC

    !========================================================
    !  MAIN COMMUNICATION CYCLE
    !========================================================

    PROC CommCycle()

        EnsureConnected;

        IF NOT IsSocketConnected() THEN
            WaitTime cReconnectWait;
            RETURN;
        ENDIF

        BuildTxFrame;

        rxFrame := "";
        SocketSend socket1\Str:=txFrame;
        SocketReceive socket1\Str:=rxFrame\Time:=cRxTimeout;

        IF NOT ExtractPayload(rxFrame) THEN
            HandleInvalidFrame;
            RETURN;
        ENDIF

        ParseRxPayload rxPayload;

        CommOK := TRUE;
        CommFault := FALSE;
        NewData := TRUE;
        CommLastError := 0;
        CommTimeoutCycles := 0;
        CommRxFrameCounter := CommRxFrameCounter + 1;
        CommTxFrameCounter := CommTxFrameCounter + 1;

    ERROR

        HandleCommError ERRNO;
        RETURN;

    ENDPROC

    !========================================================
    !  SOCKET MANAGEMENT
    !========================================================

    PROC EnsureConnected()

        IF IsSocketConnected() THEN
            RETURN;
        ENDIF

        TrySocketOpen;

    ENDPROC


    PROC TrySocketOpen()

        CloseSocketSafe;

        SocketCreate socket1;
        bSocketCreated := TRUE;

        SocketConnect socket1, cRemoteIP, cPort\Time:=cRxTimeout;

        CommOK := TRUE;
        CommFault := FALSE;
        CommLastError := 0;
        CommTimeoutCycles := 0;

    ERROR

        CommOK := FALSE;
        CommFault := TRUE;
        CommLastError := ERRNO;
        NewData := FALSE;

        CloseSocketSafe;
        WaitTime cReconnectWait;
        RETURN;

    ENDPROC


    FUNC bool IsSocketConnected()

        IF NOT bSocketCreated THEN
            RETURN FALSE;
        ENDIF

        socketState := SocketGetStatus(socket1);

        IF socketState = SOCKET_CONNECTED THEN
            RETURN TRUE;
        ELSE
            RETURN FALSE;
        ENDIF

    ENDFUNC


    PROC CloseSocketSafe()

        IF bSocketCreated THEN
            SocketClose socket1;
        ENDIF

        bSocketCreated := FALSE;

    ERROR
        bSocketCreated := FALSE;
        RETURN;
    ENDPROC

    !========================================================
    !  ERROR HANDLING
    !========================================================

    PROC HandleCommError(num nError)

        CommOK := FALSE;
        NewData := FALSE;
        CommLastError := nError;

        IF nError = ERR_SOCK_TIMEOUT THEN

            CommTimeoutCycles := CommTimeoutCycles + 1;

            IF CommTimeoutCycles >= cMaxTimeoutCycles THEN
                CommFault := TRUE;
            ENDIF

        ELSEIF nError = ERR_SOCK_CLOSED THEN

            CommFault := TRUE;

        ELSE

            CommFault := TRUE;

        ENDIF

        CloseSocketSafe;
        WaitTime cReconnectWait;

    ENDPROC


    PROC HandleInvalidFrame()

        CommOK := FALSE;
        CommFault := TRUE;
        NewData := FALSE;
        CommLastError := -1;

    ENDPROC

    !========================================================
    !  FRAME BUILDING
    !========================================================

    PROC BuildTxFrame()

        VAR num i;

        txPayload := "";

        FOR i FROM 1 TO 6 DO
            txPayload := AddField(txPayload, NumToStr(VO_Bits{i},0));
        ENDFOR

        FOR i FROM 1 TO 26 DO
            txPayload := AddField(txPayload, NumToStr(VO_Status{i},0));
        ENDFOR

        FOR i FROM 1 TO 26 DO
            txPayload := AddField(txPayload, NumToStr(VO_Parameters{i},0));
        ENDFOR

        txFrame := cFrameStart + txPayload + cFrameEnd;

    ENDPROC


    FUNC string AddField(string sCurrent, string sField)

        IF StrLen(sCurrent) = 0 THEN
            RETURN sField;
        ELSE
            RETURN sCurrent + "," + sField;
        ENDIF

    ENDFUNC

    !========================================================
    !  FRAME PARSER
    !========================================================

    FUNC bool ExtractPayload(string sFrame)

        VAR num nLen;

        nLen := StrLen(sFrame);

        IF nLen < 3 THEN
            RETURN FALSE;
        ENDIF

        IF StrPart(sFrame,1,1) <> cFrameStart THEN
            RETURN FALSE;
        ENDIF

        IF StrPart(sFrame,nLen,1) <> cFrameEnd THEN
            RETURN FALSE;
        ENDIF

        rxPayload := StrPart(sFrame,2,nLen-2);
        RETURN TRUE;

    ENDFUNC


    PROC ParseRxPayload(string sPayload)

        VAR num i;
        VAR num startPos;
        VAR num commaPos;
        VAR num totalLen;
        VAR string token;
        VAR num tmp;
        VAR bool ok;

        startPos := 1;
        totalLen := StrLen(sPayload);

        FOR i FROM 1 TO 6 DO
            ReadNextField sPayload, startPos, totalLen, i < 58, token;
            ok := StrToVal(token, tmp);
            IF NOT ok THEN
                HandleInvalidFrame;
                RETURN;
            ENDIF
            VI_Bits{i} := tmp;
        ENDFOR

        FOR i FROM 1 TO 26 DO
            ReadNextField sPayload, startPos, totalLen, TRUE, token;
            ok := StrToVal(token, tmp);
            IF NOT ok THEN
                HandleInvalidFrame;
                RETURN;
            ENDIF
            VI_Status{i} := tmp;
        ENDFOR

        FOR i FROM 1 TO 26 DO
            ReadNextField sPayload, startPos, totalLen, i < 26, token;
            ok := StrToVal(token, tmp);
            IF NOT ok THEN
                HandleInvalidFrame;
                RETURN;
            ENDIF
            VI_Parameters{i} := tmp;
        ENDFOR

    ENDPROC


    PROC ReadNextField(string sPayload, VAR num startPos, num totalLen, bool expectComma, VAR string token)

        VAR num commaPos;

        IF expectComma THEN
            commaPos := StrFind(sPayload, startPos, ",");
            IF commaPos = 0 THEN
                token := "";
                RETURN;
            ENDIF

            token := StrPart(sPayload, startPos, commaPos - startPos);
            startPos := commaPos + 1;
        ELSE
            token := StrPart(sPayload, startPos, totalLen - startPos + 1);
            startPos := totalLen + 1;
        ENDIF

    ENDPROC

ENDMODULE
