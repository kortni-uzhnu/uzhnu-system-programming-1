; System Programming - 1, laboratory 1, variant 1.
; X = 8354, Y = 101, N = 1. Widths follow the handout: 8/16/32 bits.
; Only values representable in each signed/unsigned type are declared.
OPTION CASEMAP:NONE
EXTERN ExitProcess:PROC

.data
PUBLIC data_begin, data_end
data_begin LABEL BYTE

; Byte: unsigned 8-bit, 0..255. The four X values and negative Y values do not fit.
PUBLIC byte_y_plus_n, byte_y_minus_n
byte_y_plus_n       DB 102
byte_y_minus_n      DB 100

; ShortInt: signed 8-bit, -128..127. The four X values do not fit.
PUBLIC shortint_y_plus_n, shortint_y_minus_n
PUBLIC shortint_neg_y_minus_n, shortint_neg_y_plus_n
shortint_y_plus_n       DB 102
shortint_y_minus_n      DB 100
shortint_neg_y_minus_n  DB -102
shortint_neg_y_plus_n   DB -100

; Word: unsigned 16-bit, 0..65535. Negative values do not fit.
PUBLIC word_x_plus_n, word_x_minus_n, word_y_plus_n, word_y_minus_n
word_x_plus_n       DW 8355
word_x_minus_n      DW 8353
word_y_plus_n       DW 102
word_y_minus_n      DW 100

; Integer: signed 16-bit, -32768..32767. All eight values fit.
PUBLIC integer_x_plus_n, integer_x_minus_n
PUBLIC integer_neg_x_minus_n, integer_neg_x_plus_n
PUBLIC integer_y_plus_n, integer_y_minus_n
PUBLIC integer_neg_y_minus_n, integer_neg_y_plus_n
integer_x_plus_n       DW 8355
integer_x_minus_n      DW 8353
integer_neg_x_minus_n  DW -8355
integer_neg_x_plus_n   DW -8353
integer_y_plus_n       DW 102
integer_y_minus_n      DW 100
integer_neg_y_minus_n  DW -102
integer_neg_y_plus_n   DW -100

; LongWord: unsigned 32-bit, 0..4294967295. Negative values do not fit.
PUBLIC longword_x_plus_n, longword_x_minus_n
PUBLIC longword_y_plus_n, longword_y_minus_n
longword_x_plus_n   DD 8355
longword_x_minus_n  DD 8353
longword_y_plus_n   DD 102
longword_y_minus_n  DD 100

; LongInt: signed 32-bit, -2147483648..2147483647. All eight values fit.
PUBLIC longint_x_plus_n, longint_x_minus_n
PUBLIC longint_neg_x_minus_n, longint_neg_x_plus_n
PUBLIC longint_y_plus_n, longint_y_minus_n
PUBLIC longint_neg_y_minus_n, longint_neg_y_plus_n
longint_x_plus_n       DD 8355
longint_x_minus_n      DD 8353
longint_neg_x_minus_n  DD -8355
longint_neg_x_plus_n   DD -8353
longint_y_plus_n       DD 102
longint_y_minus_n      DD 100
longint_neg_y_minus_n  DD -102
longint_neg_y_plus_n   DD -100
data_end LABEL BYTE

.code
; Data declarations are the lab task. This entry point permits a smoke test.
WinMain PROC FRAME
    sub rsp, 28h
    .allocstack 28h
    .endprolog
    xor ecx, ecx
    call ExitProcess
    int 3
WinMain ENDP
END
