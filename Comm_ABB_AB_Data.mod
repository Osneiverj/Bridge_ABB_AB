MODULE Comm_ABB_AB_Data

    !========================================================
    !  ABB <-> Python communication shared data
    !========================================================

    PERS bool CommOK := FALSE;
    PERS bool CommFault := FALSE;
    PERS bool NewData := FALSE;

    PERS num CommLastError := 0;
    PERS num CommTimeoutCycles := 0;

    ! Virtual inputs (Python -> ABB)
    PERS num  VI_Bits{6} := [0,0,0,0,0,0];
    PERS num  VI_Status{26} := [
        0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0
    ];
    PERS num  VI_Parameters{26} := [
        0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0
    ];

    ! Virtual outputs (ABB -> Python)
    PERS num  VO_Bits{6} := [0,0,0,0,0,0];
    PERS num  VO_Status{26} := [
        0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0
    ];
    PERS num  VO_Parameters{26} := [
        0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0
    ];

ENDMODULE
