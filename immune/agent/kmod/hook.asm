;
; SENTINEL IMMUNE — DragonFlyBSD Syscall Hook
;
; Real assembly syscall interception.
; Hooks sysent table at kernel level.
;
; For DragonFlyBSD 6.x / AMD64
;

bits 64
default rel

; System constants
%define SYS_read        3
%define SYS_write       4
%define SYS_open        5
%define SYS_close       6
%define SYS_execve      59
%define SYS_connect     98

; Error codes
%define EPERM           1

; Kernel memory offset (DragonFlyBSD specific)
%define SYSENT_BASE     0xFFFFFFFF80200000

section .data

    ; Original syscall addresses
    align 8
    orig_read:      dq 0
    orig_write:     dq 0
    orig_open:      dq 0
    orig_execve:    dq 0
    orig_connect:   dq 0

    ; Hook state
    hooks_enabled:  db 1
    
    ; Statistics
    align 8
    stat_intercepted:   dq 0
    stat_threats:       dq 0
    stat_blocked:       dq 0

section .text

global immune_hook_install
global immune_hook_remove
global immune_hook_stats

; External scanner function (C)
extern immune_kern_scan

;
; immune_read_hook - Intercept read() syscall
;
; Input:
;   rdi = struct thread *td
;   rsi = struct read_args *uap
;
; Returns:
;   rax = return value
;
immune_read_hook:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    sub     rsp, 32
    
    ; Save thread and args
    mov     r12, rdi        ; td
    mov     r13, rsi        ; uap
    
    ; Increment counter
    lock inc qword [rel stat_intercepted]
    
    ; Call original read() first
    mov     rdi, r12
    mov     rsi, r13
    call    [rel orig_read]
    
    ; Save result
    mov     rbx, rax
    
    ; Check if hooks enabled
    cmp     byte [rel hooks_enabled], 0
    je      .read_done
    
    ; Check result (rax = bytes read)
    test    rbx, rbx
    jle     .read_done
    
    ; Get buffer from uap (struct read_args)
    ;   uap->buf is at offset 8
    ;   uap->nbyte is at offset 16
    mov     rdi, [r13 + 8]      ; buf
    mov     rsi, [r13 + 16]     ; nbyte
    
    ; Limit to 4KB for scan
    cmp     rsi, 4096
    jbe     .do_scan
    mov     rsi, 4096
    
.do_scan:
    ; Call scanner
    call    immune_kern_scan
    
    ; Check threat level (rax)
    test    eax, eax
    jz      .read_done
    
    ; Threat detected - log but don't block reads
    lock inc qword [rel stat_threats]
    
.read_done:
    mov     rax, rbx        ; Restore original result
    
    add     rsp, 32
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

;
; immune_write_hook - Intercept write() syscall
;
immune_write_hook:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    sub     rsp, 32
    
    mov     r12, rdi        ; td
    mov     r13, rsi        ; uap
    
    lock inc qword [rel stat_intercepted]
    
    ; Check hooks enabled
    cmp     byte [rel hooks_enabled], 0
    je      .write_original
    
    ; Get write buffer and length
    mov     rdi, [r13 + 8]      ; buf
    mov     rsi, [r13 + 16]     ; nbyte
    
    cmp     rsi, 4096
    jbe     .write_scan
    mov     rsi, 4096
    
.write_scan:
    call    immune_kern_scan
    
    ; Check threat level
    cmp     eax, 4              ; CRITICAL
    jge     .write_block
    
.write_original:
    mov     rdi, r12
    mov     rsi, r13
    call    [rel orig_write]
    jmp     .write_done
    
.write_block:
    lock inc qword [rel stat_threats]
    lock inc qword [rel stat_blocked]
    mov     eax, EPERM          ; Return permission denied
    neg     eax
    
.write_done:
    add     rsp, 32
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

;
; immune_execve_hook - Intercept execve() syscall
;
immune_execve_hook:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    sub     rsp, 48
    
    mov     r12, rdi        ; td
    mov     r13, rsi        ; uap
    
    lock inc qword [rel stat_intercepted]
    
    cmp     byte [rel hooks_enabled], 0
    je      .exec_original
    
    ; Get filename from uap
    ; struct execve_args { char *fname; ... }
    mov     rdi, [r13]          ; fname pointer
    
    ; Calculate string length (max 256)
    xor     ecx, ecx
.strlen_loop:
    cmp     byte [rdi + rcx], 0
    je      .strlen_done
    inc     ecx
    cmp     ecx, 256
    jl      .strlen_loop
    
.strlen_done:
    mov     rsi, rcx
    mov     rdi, [r13]
    
    call    immune_kern_scan
    
    cmp     eax, 4              ; CRITICAL
    jge     .exec_block
    
.exec_original:
    mov     rdi, r12
    mov     rsi, r13
    call    [rel orig_execve]
    jmp     .exec_done
    
.exec_block:
    lock inc qword [rel stat_threats]
    lock inc qword [rel stat_blocked]
    mov     eax, EPERM
    neg     eax
    
.exec_done:
    add     rsp, 48
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

;
; immune_hook_install - Install syscall hooks
;
; Input:
;   rdi = pointer to sysent table
;
; Returns:
;   rax = 0 on success, -1 on failure
;
immune_hook_install:
    push    rbp
    mov     rbp, rsp
    push    rbx
    
    mov     rbx, rdi            ; sysent base
    
    ; Disable write protection
    mov     rax, cr0
    and     rax, 0xFFFEFFFF     ; Clear WP bit
    mov     cr0, rax
    
    ; Save original handlers
    ; sysent[n].sy_call is at offset (n * 32 + 0)
    
    ; read (SYS_read = 3)
    mov     rax, [rbx + SYS_read * 32]
    mov     [rel orig_read], rax
    lea     rax, [rel immune_read_hook]
    mov     [rbx + SYS_read * 32], rax
    
    ; write (SYS_write = 4)
    mov     rax, [rbx + SYS_write * 32]
    mov     [rel orig_write], rax
    lea     rax, [rel immune_write_hook]
    mov     [rbx + SYS_write * 32], rax
    
    ; execve (SYS_execve = 59)
    mov     rax, [rbx + SYS_execve * 32]
    mov     [rel orig_execve], rax
    lea     rax, [rel immune_execve_hook]
    mov     [rbx + SYS_execve * 32], rax
    
    ; Re-enable write protection
    mov     rax, cr0
    or      rax, 0x10000        ; Set WP bit
    mov     cr0, rax
    
    xor     eax, eax            ; Success
    
    pop     rbx
    pop     rbp
    ret

;
; immune_hook_remove - Remove syscall hooks
;
immune_hook_remove:
    push    rbp
    mov     rbp, rsp
    push    rbx
    
    mov     rbx, rdi            ; sysent base
    
    ; Disable write protection
    mov     rax, cr0
    and     rax, 0xFFFEFFFF
    mov     cr0, rax
    
    ; Restore original handlers
    mov     rax, [rel orig_read]
    test    rax, rax
    jz      .skip_read
    mov     [rbx + SYS_read * 32], rax
.skip_read:
    
    mov     rax, [rel orig_write]
    test    rax, rax
    jz      .skip_write
    mov     [rbx + SYS_write * 32], rax
.skip_write:
    
    mov     rax, [rel orig_execve]
    test    rax, rax
    jz      .skip_execve
    mov     [rbx + SYS_execve * 32], rax
.skip_execve:
    
    ; Re-enable write protection
    mov     rax, cr0
    or      rax, 0x10000
    mov     cr0, rax
    
    xor     eax, eax
    
    pop     rbx
    pop     rbp
    ret

;
; immune_hook_stats - Get hook statistics
;
; Input:
;   rdi = pointer to stats struct (3 x uint64)
;
immune_hook_stats:
    mov     rax, [rel stat_intercepted]
    mov     [rdi], rax
    
    mov     rax, [rel stat_threats]
    mov     [rdi + 8], rax
    
    mov     rax, [rel stat_blocked]
    mov     [rdi + 16], rax
    
    ret
