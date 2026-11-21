; System Programming - 1, laboratory 2, variant 1.
; Signed 64-bit calculation: (2*c - d - 23) / (a/4 - 1).
; Both divisions truncate toward zero. Every numerator operation is checked.
OPTION CASEMAP:NONE
EXTERN ExitProcess:PROC
EXTERN GetCommandLineW:PROC
EXTERN CommandLineToArgvW:PROC
EXTERN lstrcmpW:PROC
EXTERN GetStdHandle:PROC
EXTERN WriteFile:PROC
PUBLIC calculate_expression

.data
argc_value DWORD 0
argv_value QWORD 0
a_value SQWORD 0
c_value SQWORD 0
d_value SQWORD 0
result QWORD 4 DUP(0)        ; quotient, remainder, numerator, denominator
number_buffer BYTE 32 DUP(0)
help_option WORD 45,45,104,101,108,112,0 ; --help
usage_text BYTE "System Programming lab 2, variant 1",13,10
           BYTE "Expression: (2*c - d - 23) / (a/4 - 1)",13,10
           BYTE "Usage: lab_2.exe a c d",13,10
           BYTE "Inputs: signed 64-bit decimal integers; division truncates to zero.",13,10
usage_end LABEL BYTE
invalid_text BYTE "Error: supply exactly three signed 64-bit decimal integers.",13,10
invalid_end LABEL BYTE
zero_text BYTE "Error: denominator a/4 - 1 is zero.",13,10
zero_end LABEL BYTE
overflow_text BYTE "Error: signed 64-bit arithmetic overflow.",13,10
overflow_end LABEL BYTE
numerator_text BYTE "Numerator: "
numerator_end LABEL BYTE
denominator_text BYTE "Denominator: "
denominator_end LABEL BYTE
quotient_text BYTE "Quotient: "
quotient_end LABEL BYTE
remainder_text BYTE "Remainder: "
remainder_end LABEL BYTE
newline_text BYTE 13,10
newline_end LABEL BYTE

PRINT_TEXT MACRO first_label, end_label
    lea rcx, first_label
    mov edx, end_label - first_label
    call print_buffer
ENDM

.code
; ABI: RCX=a, RDX=c, R8=d, R9=pointer to four signed 64-bit results.
; EAX status: 0 success, 1 zero denominator, 2 overflow.
; Error paths leave all four output fields unchanged. Pointer must be valid.
; This leaf routine uses only volatile registers and performs all arithmetic.
calculate_expression PROC
    mov rax, rdx
    sal rax, 1               ; 2*c; OF is valid for this one-bit shift
    jo arithmetic_overflow
    sub rax, r8              ; 2*c - d
    jo arithmetic_overflow
    sub rax, 23              ; numerator
    jo arithmetic_overflow
    mov r10, rax

    mov rax, rcx
    test rax, rax
    jns divide_a
    add rax, 3               ; negative bias makes SAR truncate toward zero
divide_a:
    sar rax, 2               ; signed a/4 with truncation toward zero
    dec rax                  ; denominator; a/4 is safely inside int64 range
    mov r11, rax
    test r11, r11
    jz zero_denominator

    mov rdx, 8000000000000000h
    cmp r10, rdx
    jne divide_expression
    cmp r11, -1              ; INT64_MIN / -1 is not representable
    je arithmetic_overflow
divide_expression:
    mov rax, r10
    cqo                      ; sign-extend numerator into RDX:RAX
    idiv r11                 ; quotient RAX, remainder RDX
    mov QWORD PTR [r9], rax
    mov QWORD PTR [r9+8], rdx
    mov QWORD PTR [r9+16], r10
    mov QWORD PTR [r9+24], r11
    xor eax, eax
    ret
zero_denominator:
    mov eax, 1
    ret
arithmetic_overflow:
    mov eax, 2
    ret
calculate_expression ENDP

; Parse a null-terminated UTF-16 ASCII decimal integer.
; RCX points to text. Return RAX=value, CF=0; invalid/out of range: CF=1.
; Accumulation is unsigned so the magnitude of INT64_MIN remains valid.
parse_integer PROC
    xor r8d, r8d             ; negative flag
    cmp WORD PTR [rcx], '-'
    jne check_plus
    mov r8d, 1
    add rcx, 2
    jmp first_digit
check_plus:
    cmp WORD PTR [rcx], '+'
    jne first_digit
    add rcx, 2
first_digit:
    cmp WORD PTR [rcx], 0
    je invalid_integer
    xor eax, eax
    mov r9, 922337203685477580
parse_digit:
    movzx r10d, WORD PTR [rcx]
    test r10d, r10d
    jz parsed_integer
    sub r10d, '0'
    cmp r10d, 9
    ja invalid_integer
    cmp rax, r9
    ja invalid_integer
    jb accumulate_digit
    mov r11d, 7
    add r11d, r8d            ; final allowed digit: 7 positive, 8 negative
    cmp r10d, r11d
    ja invalid_integer
accumulate_digit:
    imul rax, rax, 10
    add rax, r10
    add rcx, 2
    jmp parse_digit
parsed_integer:
    test r8d, r8d
    jz parse_success
    neg rax                  ; INT64_MIN bit pattern is deliberately retained
parse_success:
    clc
    ret
invalid_integer:
    stc
    ret
parse_integer ENDP

; Write EDX bytes from RCX to standard output using Windows APIs.
print_buffer PROC FRAME
    sub rsp, 48h
    .allocstack 48h
    .endprolog
    mov QWORD PTR [rsp+30h], rcx
    mov DWORD PTR [rsp+38h], edx
    mov ecx, -11             ; STD_OUTPUT_HANDLE
    call GetStdHandle
    mov rcx, rax
    mov rdx, QWORD PTR [rsp+30h]
    mov r8d, DWORD PTR [rsp+38h]
    lea r9, [rsp+40h]
    mov QWORD PTR [rsp+20h], 0
    call WriteFile
    add rsp, 48h
    ret
print_buffer ENDP

; Print signed RCX, including INT64_MIN, using unsigned magnitude division.
print_number PROC
    mov rax, rcx
    xor r11d, r11d
    test rax, rax
    jns magnitude_ready
    mov r11d, 1
    neg rax
magnitude_ready:
    lea r10, number_buffer+32
    mov r8d, 10
format_digit:
    xor edx, edx
    div r8
    add dl, '0'
    dec r10
    mov BYTE PTR [r10], dl
    test rax, rax
    jnz format_digit
    test r11d, r11d
    jz number_ready
    dec r10
    mov BYTE PTR [r10], '-'
number_ready:
    mov rcx, r10
    lea rdx, number_buffer+32
    sub rdx, rcx
    jmp print_buffer         ; tail call, preserves the caller's return address
print_number ENDP

WinMain PROC FRAME
    sub rsp, 28h
    .allocstack 28h
    .endprolog
    call GetCommandLineW
    mov rcx, rax
    lea rdx, argc_value
    call CommandLineToArgvW
    test rax, rax
    jz bad_input
    mov argv_value, rax
    cmp argc_value, 2
    jne check_argument_count
    mov rcx, QWORD PTR [rax+8]
    lea rdx, help_option
    call lstrcmpW
    test eax, eax
    jnz bad_input
    PRINT_TEXT usage_text, usage_end
    xor ecx, ecx
    call ExitProcess
check_argument_count:
    cmp argc_value, 4
    jne bad_input
    mov rax, argv_value
    mov rcx, QWORD PTR [rax+8]
    call parse_integer
    jc bad_input
    mov a_value, rax
    mov rax, argv_value
    mov rcx, QWORD PTR [rax+16]
    call parse_integer
    jc bad_input
    mov c_value, rax
    mov rax, argv_value
    mov rcx, QWORD PTR [rax+24]
    call parse_integer
    jc bad_input
    mov d_value, rax

    mov rcx, a_value
    mov rdx, c_value
    mov r8, d_value
    lea r9, result
    call calculate_expression
    cmp eax, 1
    je main_zero
    cmp eax, 2
    je main_overflow
    PRINT_TEXT numerator_text, numerator_end
    mov rcx, QWORD PTR result+16
    call print_number
    PRINT_TEXT newline_text, newline_end
    PRINT_TEXT denominator_text, denominator_end
    mov rcx, QWORD PTR result+24
    call print_number
    PRINT_TEXT newline_text, newline_end
    PRINT_TEXT quotient_text, quotient_end
    mov rcx, QWORD PTR result
    call print_number
    PRINT_TEXT newline_text, newline_end
    PRINT_TEXT remainder_text, remainder_end
    mov rcx, QWORD PTR result+8
    call print_number
    PRINT_TEXT newline_text, newline_end
    xor ecx, ecx
    call ExitProcess
bad_input:
    PRINT_TEXT invalid_text, invalid_end
    PRINT_TEXT usage_text, usage_end
    mov ecx, 2
    call ExitProcess
main_zero:
    PRINT_TEXT zero_text, zero_end
    mov ecx, 3
    call ExitProcess
main_overflow:
    PRINT_TEXT overflow_text, overflow_end
    mov ecx, 4
    call ExitProcess
    int 3
WinMain ENDP
END
