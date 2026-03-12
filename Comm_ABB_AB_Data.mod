MODULE Comm_ABB_AB_Data

    !========================================================
    !  SHARED VIRTUAL IMAGE
    !========================================================

    ! Virtual inputs written by the communication task.
    PERS num VI_Bits{6} := [0,0,0,0,0,0];
    PERS num VI_Status{26} := [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
    PERS num VI_Parameters{26} := [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];

    ! Virtual outputs written by the execution task.
    PERS num VO_Bits{6} := [0,0,0,0,0,0];
    PERS num VO_Status{26} := [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
    PERS num VO_Parameters{26} := [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];

    !========================================================
    !  COMMUNICATION STATUS
    !========================================================

    PERS bool CommOK := FALSE;
    PERS bool CommFault := TRUE;
    PERS bool NewData := FALSE;

    PERS num CommLastError := 0;
    PERS num CommTimeoutCycles := 0;
    PERS num CommRxFrameCounter := 0;
    PERS num CommTxFrameCounter := 0;

    !========================================================
    !  RESET PROCEDURES
    !========================================================

    PROC ResetViData()

        VAR num i;

        FOR i FROM 1 TO 6 DO
            VI_Bits{i} := 0;
        ENDFOR

        FOR i FROM 1 TO 26 DO
            VI_Status{i} := 0;
            VI_Parameters{i} := 0;
        ENDFOR

        NewData := FALSE;

    ENDPROC


    PROC ResetCommState()

        CommOK := FALSE;
        CommFault := TRUE;
        CommLastError := 0;
        CommTimeoutCycles := 0;
        CommRxFrameCounter := 0;
        CommTxFrameCounter := 0;

    ENDPROC


    PROC ResetVoData()

        VAR num i;

        FOR i FROM 1 TO 6 DO
            VO_Bits{i} := 0;
        ENDFOR

        FOR i FROM 1 TO 26 DO
            VO_Status{i} := 0;
            VO_Parameters{i} := 0;
        ENDFOR

    ENDPROC

    !========================================================
    !  BIT UTILITIES
    !========================================================

    FUNC num BitMask(num nBit)

        VAR num i;
        VAR num mask;

        mask := 1;
        i := 0;

        WHILE i < nBit DO
            mask := mask * 2;
            i := i + 1;
        ENDWHILE

        RETURN mask;

    ENDFUNC


    FUNC bool GetBit(num nWord, num nBit)

        VAR num mask;
        VAR num q;
        VAR num rem;

        mask := BitMask(nBit);
        q := Trunc(nWord / mask\Dec:=0);
        rem := q - (2 * Trunc(q / 2\Dec:=0));

        IF rem = 1 THEN
            RETURN TRUE;
        ELSE
            RETURN FALSE;
        ENDIF

    ENDFUNC


    FUNC num SetBit(num nWord, num nBit, bool bValue)

        VAR num mask;
        VAR bool current;

        mask := BitMask(nBit);
        current := GetBit(nWord, nBit);

        IF bValue AND (NOT current) THEN
            nWord := nWord + mask;
        ELSEIF (NOT bValue) AND current THEN
            nWord := nWord - mask;
        ENDIF

        RETURN nWord;

    ENDFUNC

ENDMODULE
