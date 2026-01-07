# ============================================================================
# IMMUNE Security Makefile Fragment
# Include this in your main Makefile: include security.mk
# ============================================================================

# Compiler detection
CC ?= cc
CC_IS_CLANG := $(shell $(CC) --version 2>/dev/null | grep -qi clang && echo 1)
CC_IS_GCC   := $(shell $(CC) --version 2>/dev/null | grep -qi gcc && echo 1)

# ============================================================================
# Core Security Flags (Always Enable)
# ============================================================================

SECURITY_CFLAGS := \
    -Wall \
    -Wextra \
    -Wpedantic \
    -Werror \
    -Wformat=2 \
    -Wformat-security \
    -Wformat-overflow=2 \
    -Wconversion \
    -Wsign-conversion \
    -Wcast-qual \
    -Wcast-align \
    -Wshadow \
    -Wstrict-prototypes \
    -Wmissing-prototypes \
    -Wredundant-decls \
    -Wnull-dereference \
    -Wdouble-promotion

# ============================================================================
# Stack Protection
# ============================================================================

SECURITY_CFLAGS += \
    -fstack-protector-strong

# Stack clash protection (GCC 8+, Clang 11+)
SECURITY_CFLAGS += \
    -fstack-clash-protection

# ============================================================================
# Runtime Checks
# ============================================================================

# FORTIFY_SOURCE requires optimization
SECURITY_CFLAGS += \
    -D_FORTIFY_SOURCE=3

# Trap on undefined behavior (optional, may break some code)
# SECURITY_CFLAGS += -ftrapv

# ============================================================================
# Position Independent Code (for ASLR)
# ============================================================================

SECURITY_CFLAGS_EXE := \
    -fPIE

SECURITY_LDFLAGS_EXE := \
    -pie

SECURITY_CFLAGS_LIB := \
    -fPIC

# ============================================================================
# Control Flow Integrity (Intel CET, x86_64 only)
# ============================================================================

ifeq ($(shell uname -m),x86_64)
    ifdef CC_IS_GCC
        SECURITY_CFLAGS += -fcf-protection=full
    endif
    ifdef CC_IS_CLANG
        SECURITY_CFLAGS += -fcf-protection=full
    endif
endif

# ============================================================================
# Linker Hardening
# ============================================================================

SECURITY_LDFLAGS := \
    -Wl,-z,relro \
    -Wl,-z,now \
    -Wl,-z,noexecstack \
    -Wl,-z,separate-code

# ============================================================================
# Kernel Module Specific Flags
# ============================================================================

KMOD_SECURITY_CFLAGS := \
    -fno-common \
    -fno-delete-null-pointer-checks \
    -fno-strict-overflow \
    -fno-strict-aliasing \
    -fno-omit-frame-pointer

# ============================================================================
# Debug/Sanitizer Build (Development Only)
# ============================================================================

DEBUG_CFLAGS := \
    -g3 \
    -O1 \
    -fno-omit-frame-pointer \
    -fno-optimize-sibling-calls

ASAN_CFLAGS := \
    $(DEBUG_CFLAGS) \
    -fsanitize=address \
    -fsanitize=leak

UBSAN_CFLAGS := \
    $(DEBUG_CFLAGS) \
    -fsanitize=undefined \
    -fno-sanitize-recover=all

TSAN_CFLAGS := \
    $(DEBUG_CFLAGS) \
    -fsanitize=thread

# Full sanitizer build
SANITIZER_CFLAGS := \
    $(DEBUG_CFLAGS) \
    -fsanitize=address,undefined \
    -fno-sanitize-recover=all

SANITIZER_LDFLAGS := \
    -fsanitize=address,undefined

# ============================================================================
# Banned Functions Check (via grep in CI)
# ============================================================================

BANNED_FUNCTIONS := \
    gets \
    sprintf \
    vsprintf \
    strcpy \
    strcat \
    strncpy \
    strncat \
    scanf \
    sscanf \
    fscanf \
    vscanf \
    vsscanf \
    vfscanf \
    realpath \
    getwd \
    mktemp

# Generate regex for banned functions
BANNED_REGEX := $(shell echo $(BANNED_FUNCTIONS) | tr ' ' '|')

# ============================================================================
# Targets
# ============================================================================

.PHONY: security-check banned-check

# Check for banned functions in source
banned-check:
	@echo "Checking for banned functions..."
	@if grep -rE '\b($(BANNED_REGEX))\s*\(' --include='*.c' --include='*.h' .; then \
		echo "ERROR: Banned functions found!"; \
		exit 1; \
	else \
		echo "OK: No banned functions found."; \
	fi

# Run static analysis
security-check: banned-check
	@echo "Running cppcheck..."
	@cppcheck --enable=all --error-exitcode=1 \
		--suppress=missingIncludeSystem \
		--suppress=unusedFunction \
		-I include/ \
		src/

# ============================================================================
# Usage Example
# ============================================================================

# In your main Makefile:
#
# include security.mk
#
# # For executables:
# CFLAGS += $(SECURITY_CFLAGS) $(SECURITY_CFLAGS_EXE)
# LDFLAGS += $(SECURITY_LDFLAGS) $(SECURITY_LDFLAGS_EXE)
#
# # For libraries:
# CFLAGS += $(SECURITY_CFLAGS) $(SECURITY_CFLAGS_LIB)
# LDFLAGS += $(SECURITY_LDFLAGS)
#
# # For kernel modules:
# CFLAGS += $(SECURITY_CFLAGS) $(KMOD_SECURITY_CFLAGS)
#
# # For debug/sanitizer builds:
# ifeq ($(BUILD),debug)
#     CFLAGS += $(SANITIZER_CFLAGS)
#     LDFLAGS += $(SANITIZER_LDFLAGS)
# endif
