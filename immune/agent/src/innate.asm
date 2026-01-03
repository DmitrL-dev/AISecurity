; ===========================================================================
; SENTINEL IMMUNE — Innate Immunity Layer (x86-64)
; 
; Pattern Recognition Receptors for syscall content analysis.
; Fast, non-specific first line of defense.
;
; Target: DragonFlyBSD / Linux x86-64
; ===========================================================================

section .data
    ; Pattern: "ignore" (injection indicator)
    pattern_ignore:     db "ignore", 0
    pattern_ignore_len: equ $ - pattern_ignore - 1
    
    ; Pattern: "previous instructions" 
    pattern_prev:       db "previous", 0
    pattern_prev_len:   equ $ - pattern_prev - 1
    
    ; Pattern: "system prompt"
    pattern_sysprompt:  db "system prompt", 0
    pattern_sysprompt_len: equ $ - pattern_sysprompt - 1
    
    ; Pattern: "DAN" (jailbreak)
    pattern_dan:        db "DAN", 0
    pattern_dan_len:    equ $ - pattern_dan - 1

section .bss
    match_count:        resq 1
    last_match_type:    resq 1

section .text
    global immune_innate_scan
    global immune_get_stats

; ---------------------------------------------------------------------------
; immune_innate_scan
; 
; Fast pattern scan using SIMD when available.
; 
; Input:
;   rdi = pointer to buffer
;   rsi = buffer length
; 
; Output:
;   rax = threat level (0=none, 1=low, 2=medium, 3=high, 4=critical)
; ---------------------------------------------------------------------------
immune_innate_scan:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13
    push r14
    
    mov r12, rdi            ; save buffer ptr
    mov r13, rsi            ; save length
    xor r14, r14            ; threat level = 0
    
    ; Check for "ignore"
    lea rsi, [rel pattern_ignore]
    mov rdx, pattern_ignore_len
    call .find_pattern
    test rax, rax
    jz .check_prev
    mov r14, 3              ; HIGH threat
    jmp .done
    
.check_prev:
    mov rdi, r12
    mov rsi, r13
    lea rdx, [rel pattern_prev]
    mov rcx, pattern_prev_len
    call .find_pattern
    test rax, rax
    jz .check_dan
    mov r14, 2              ; MEDIUM threat
    jmp .done

.check_dan:
    mov rdi, r12
    mov rsi, r13
    lea rdx, [rel pattern_dan]
    mov rcx, pattern_dan_len
    call .find_pattern
    test rax, rax
    jz .done
    mov r14, 4              ; CRITICAL threat

.done:
    ; Update stats
    test r14, r14
    jz .no_match
    inc qword [rel match_count]
    mov [rel last_match_type], r14
    
.no_match:
    mov rax, r14
    
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret

; ---------------------------------------------------------------------------
; .find_pattern (internal)
;
; Simple byte-by-byte pattern search.
; TODO: Replace with SIMD (AVX2) for production.
;
; Input:
;   rdi = haystack
;   rsi = haystack_len  
;   rdx = needle
;   rcx = needle_len
;
; Output:
;   rax = 1 if found, 0 if not
; ---------------------------------------------------------------------------
.find_pattern:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13
    push r14
    push r15
    
    mov r12, rdi            ; haystack
    mov r13, rsi            ; haystack_len
    mov r14, rdx            ; needle
    mov r15, rcx            ; needle_len
    
    ; Check if needle fits
    cmp r13, r15
    jl .not_found
    
    xor rbx, rbx            ; position in haystack
    
.search_loop:
    mov rax, r13
    sub rax, rbx
    cmp rax, r15
    jl .not_found
    
    ; Compare at current position
    xor rcx, rcx            ; position in needle
    
.compare_loop:
    cmp rcx, r15
    je .found               ; matched all chars
    
    mov al, [r12 + rbx]
    add al, 0               ; load haystack char
    mov al, [r12 + rbx + rcx]
    
    ; Case-insensitive compare
    cmp al, 'A'
    jl .no_upper1
    cmp al, 'Z'
    jg .no_upper1
    add al, 32              ; to lowercase
.no_upper1:
    
    mov ah, [r14 + rcx]
    cmp ah, 'A'
    jl .no_upper2
    cmp ah, 'Z'
    jg .no_upper2
    add ah, 32
.no_upper2:
    
    cmp al, ah
    jne .next_pos
    
    inc rcx
    jmp .compare_loop
    
.next_pos:
    inc rbx
    jmp .search_loop
    
.found:
    mov rax, 1
    jmp .find_done
    
.not_found:
    xor rax, rax
    
.find_done:
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret

; ---------------------------------------------------------------------------
; immune_get_stats
;
; Get scan statistics.
;
; Output:
;   rax = total matches
;   rdx = last match type
; ---------------------------------------------------------------------------
immune_get_stats:
    mov rax, [rel match_count]
    mov rdx, [rel last_match_type]
    ret
