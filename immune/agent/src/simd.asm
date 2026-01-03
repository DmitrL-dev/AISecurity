; SENTINEL IMMUNE — SIMD Pattern Matching (AVX2)
;
; Ultra-fast pattern matching using AVX2 256-bit operations.
; Processes 32 bytes per iteration.
;
; Calling convention: System V AMD64
;   rdi = pointer to data
;   rsi = length
;   rdx = pointer to patterns array
;   rcx = pattern count
;   returns: threat level (rax)

section .data
    align 32
    ; Pre-computed pattern signatures (first 32 bytes of each pattern)
    pattern_ignore:     db "ignore all previous instruc", 0, 0, 0, 0
    pattern_jailbreak:  db "jailbreak                   ", 0, 0
    pattern_bypass:     db "bypass                      ", 0, 0
    pattern_system:     db "system prompt:              ", 0, 0
    
    ; Lowercase conversion mask
    lowercase_mask:     times 32 db 0x20
    
    ; Character range checks
    char_A:             times 32 db 'A'
    char_Z:             times 32 db 'Z'

section .text
    global immune_simd_scan_avx2
    global immune_simd_scan_sse42

; ==================== AVX2 Scanner ====================
; threat_level_t immune_simd_scan_avx2(const char *data, size_t length)
;
immune_simd_scan_avx2:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    
    ; rdi = data pointer
    ; rsi = length
    
    xor     eax, eax            ; threat_level = 0
    
    cmp     rsi, 32
    jb      .avx2_short         ; Too short for AVX2
    
    ; Load pattern to search for
    vmovdqa ymm1, [rel pattern_ignore]
    vmovdqa ymm2, [rel lowercase_mask]
    vmovdqa ymm3, [rel char_A]
    vmovdqa ymm4, [rel char_Z]
    
    mov     r12, rdi            ; data pointer
    mov     r13, rsi            ; remaining length
    
.avx2_loop:
    cmp     r13, 32
    jb      .avx2_remainder
    
    ; Load 32 bytes of input
    vmovdqu ymm0, [r12]
    
    ; Convert to lowercase
    ; mask = (data >= 'A') & (data <= 'Z')
    vpcmpgtb ymm5, ymm0, ymm3       ; data > 'A'-1
    vpcmpgtb ymm6, ymm4, ymm0       ; 'Z'+1 > data (data <= 'Z')
    vpand   ymm5, ymm5, ymm6        ; mask for uppercase
    vpand   ymm6, ymm5, ymm2        ; 0x20 where uppercase
    vpor    ymm0, ymm0, ymm6        ; add 0x20 to uppercase
    
    ; Compare with pattern
    vpcmpeqb ymm5, ymm0, ymm1
    vpmovmskb ecx, ymm5
    
    ; Check if first 6 chars match "ignore"
    and     ecx, 0x3F               ; First 6 bytes
    cmp     ecx, 0x3F
    jne     .avx2_next
    
    ; Found potential match - set threat level high
    mov     eax, 3                  ; THREAT_HIGH
    jmp     .avx2_done

.avx2_next:
    add     r12, 32
    sub     r13, 32
    jmp     .avx2_loop

.avx2_remainder:
    ; Handle remaining bytes with scalar code
    test    r13, r13
    jz      .avx2_done
    
    ; Simple byte-by-byte check for remaining
    mov     r14, r12
    
.avx2_scalar:
    cmp     r13, 6
    jb      .avx2_done
    
    ; Check for "ignore" (lowercase)
    movzx   ecx, byte [r14]
    or      cl, 0x20
    cmp     cl, 'i'
    jne     .avx2_scalar_next
    
    movzx   ecx, byte [r14+1]
    or      cl, 0x20
    cmp     cl, 'g'
    jne     .avx2_scalar_next
    
    movzx   ecx, byte [r14+2]
    or      cl, 0x20
    cmp     cl, 'n'
    jne     .avx2_scalar_next
    
    movzx   ecx, byte [r14+3]
    or      cl, 0x20
    cmp     cl, 'o'
    jne     .avx2_scalar_next
    
    movzx   ecx, byte [r14+4]
    or      cl, 0x20
    cmp     cl, 'r'
    jne     .avx2_scalar_next
    
    movzx   ecx, byte [r14+5]
    or      cl, 0x20
    cmp     cl, 'e'
    jne     .avx2_scalar_next
    
    ; Match found!
    mov     eax, 3                  ; THREAT_HIGH
    jmp     .avx2_done

.avx2_scalar_next:
    inc     r14
    dec     r13
    jmp     .avx2_scalar

.avx2_short:
    ; Data too short, use scalar
    mov     r14, rdi
    mov     r13, rsi
    jmp     .avx2_scalar

.avx2_done:
    vzeroupper
    
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; ==================== SSE4.2 Scanner ====================
; threat_level_t immune_simd_scan_sse42(const char *data, size_t length)
;
immune_simd_scan_sse42:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    
    xor     eax, eax
    
    cmp     rsi, 16
    jb      .sse42_short
    
    ; Load pattern
    movdqa  xmm1, [rel pattern_ignore]
    
    mov     r12, rdi
    mov     r13, rsi

.sse42_loop:
    cmp     r13, 16
    jb      .sse42_remainder
    
    ; Load 16 bytes
    movdqu  xmm0, [r12]
    
    ; Use PCMPISTRI for pattern matching
    ; imm8 = 0x4C: equal ordered, negative polarity
    pcmpistri xmm1, xmm0, 0x4C
    
    jnc     .sse42_next
    
    ; Match found
    mov     eax, 3                  ; THREAT_HIGH
    jmp     .sse42_done

.sse42_next:
    add     r12, 16
    sub     r13, 16
    jmp     .sse42_loop

.sse42_remainder:
.sse42_short:
    ; Scalar fallback
    ; (Similar to AVX2 scalar section)
    
.sse42_done:
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret
