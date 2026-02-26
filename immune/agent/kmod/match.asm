;
; SENTINEL IMMUNE — SIMD Pattern Matcher
;
; High-performance pattern matching using AVX2/SSE4.2.
; Matches multiple patterns simultaneously.
;

bits 64
default rel

section .data

    ; Pattern constants - jailbreak signatures
    align 32
    pat_ignore:     db "ignore", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    
    pat_jailbreak:  db "jailbreak", 0, 0, 0, 0, 0, 0, 0
                    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    
    pat_bypass:     db "bypass", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    
    pat_system:     db "system prompt", 0, 0, 0
                    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    
    ; Lowercase conversion
    align 32
    case_mask:      times 32 db 0x20
    
    ; Range constants
    align 32
    char_A:         times 32 db 'A'
    char_Z:         times 32 db 'Z'

section .bss

    ; Result buffer
    align 8
    match_offset:   resq 1
    match_pattern:  resd 1
    match_level:    resd 1

section .text

global immune_match_avx2
global immune_match_sse42
global immune_match_result

;
; immune_match_avx2 - AVX2 pattern matching
;
; Input:
;   rdi = data pointer
;   rsi = data length
;
; Output:
;   rax = threat level (0-4)
;
immune_match_avx2:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    
    ; Clear result
    xor     eax, eax
    mov     [rel match_offset], rax
    mov     [rel match_pattern], eax
    mov     [rel match_level], eax
    
    ; Check minimum length
    cmp     rsi, 6
    jb      .done
    
    mov     r12, rdi                ; data ptr
    mov     r13, rsi                ; length
    xor     r14d, r14d              ; max threat level found
    
    ; Load conversion mask
    vmovdqa ymm2, [rel case_mask]
    vmovdqa ymm3, [rel char_A]
    vmovdqa ymm4, [rel char_Z]
    
.process_chunk:
    cmp     r13, 32
    jb      .process_tail
    
    ; Load 32 bytes
    vmovdqu ymm0, [r12]
    
    ; Convert to lowercase
    ; mask = (char >= 'A') && (char <= 'Z')
    vpcmpgtb ymm5, ymm0, ymm3           ; > 'A'-1
    vpcmpgtb ymm6, ymm4, ymm0           ; < 'Z'+1
    vpand   ymm5, ymm5, ymm6
    vpand   ymm6, ymm5, ymm2            ; 0x20 where uppercase
    vpor    ymm0, ymm0, ymm6            ; to lowercase
    
    ; Check pattern 1: "ignore"
    vmovdqa ymm1, [rel pat_ignore]
    vpcmpeqb ymm5, ymm0, ymm1
    vpmovmskb ecx, ymm5
    and     ecx, 0x3F                   ; First 6 chars
    cmp     ecx, 0x3F
    jne     .check_jailbreak
    
    ; "ignore" found - HIGH threat
    mov     r14d, 3
    mov     [rel match_pattern], dword 1
    mov     [rel match_level], r14d
    sub     r12, rdi
    mov     [rel match_offset], r12
    jmp     .done
    
.check_jailbreak:
    vmovdqa ymm1, [rel pat_jailbreak]
    vpcmpeqb ymm5, ymm0, ymm1
    vpmovmskb ecx, ymm5
    and     ecx, 0x1FF                  ; First 9 chars
    cmp     ecx, 0x1FF
    jne     .check_bypass
    
    ; "jailbreak" found - CRITICAL
    mov     r14d, 4
    mov     [rel match_pattern], dword 2
    mov     [rel match_level], r14d
    sub     r12, rdi
    mov     [rel match_offset], r12
    jmp     .done
    
.check_bypass:
    vmovdqa ymm1, [rel pat_bypass]
    vpcmpeqb ymm5, ymm0, ymm1
    vpmovmskb ecx, ymm5
    and     ecx, 0x3F
    cmp     ecx, 0x3F
    jne     .next_chunk
    
    ; "bypass" found - MEDIUM
    cmp     r14d, 2
    jge     .next_chunk
    mov     r14d, 2
    mov     [rel match_pattern], dword 3
    mov     [rel match_level], r14d
    
.next_chunk:
    add     r12, 1                      ; Slide by 1 for overlap
    dec     r13
    cmp     r13, 6
    jge     .process_chunk
    jmp     .done
    
.process_tail:
    ; Scalar fallback for remaining bytes
    cmp     r13, 6
    jb      .done
    
.scalar_loop:
    ; Check for "ignore"
    movzx   ecx, byte [r12]
    or      cl, 0x20
    cmp     cl, 'i'
    jne     .scalar_next
    
    mov     r15, r12
    lea     rbx, [rel pat_ignore]
    mov     ecx, 6
    
.scalar_cmp:
    movzx   eax, byte [r15]
    or      al, 0x20
    cmp     al, [rbx]
    jne     .scalar_next
    inc     r15
    inc     rbx
    dec     ecx
    jnz     .scalar_cmp
    
    ; Match found
    mov     r14d, 3
    jmp     .done
    
.scalar_next:
    inc     r12
    dec     r13
    cmp     r13, 6
    jge     .scalar_loop
    
.done:
    mov     eax, r14d
    
    vzeroupper
    
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

;
; immune_match_sse42 - SSE4.2 pattern matching using PCMPISTRI
;
immune_match_sse42:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    
    xor     eax, eax
    
    cmp     rsi, 6
    jb      .sse_done
    
    mov     r12, rdi
    mov     r13, rsi
    
    ; Load patterns into SSE registers
    movdqa  xmm1, [rel pat_ignore]
    
.sse_loop:
    cmp     r13, 16
    jb      .sse_remainder
    
    movdqu  xmm0, [r12]
    
    ; PCMPISTRI: find substring
    ; imm8 = 0x0C: equal ordered
    pcmpistri xmm1, xmm0, 0x0C
    
    jnc     .sse_no_match
    
    ; Match found at position rcx
    mov     eax, 3                      ; HIGH threat
    jmp     .sse_done
    
.sse_no_match:
    add     r12, 1
    dec     r13
    jmp     .sse_loop
    
.sse_remainder:
    ; Fallback to scalar (handled by caller)
    
.sse_done:
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

;
; immune_match_result - Get last match result
;
; Output:
;   rax = offset
;   rdx = pattern ID
;   rcx = threat level
;
immune_match_result:
    mov     rax, [rel match_offset]
    mov     edx, [rel match_pattern]
    mov     ecx, [rel match_level]
    ret
