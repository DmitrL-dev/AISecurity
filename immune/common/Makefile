# IMMUNE Common Library — Makefile
# Build safe_memory and tls_transport modules

CC       ?= cc
CFLAGS   := -Wall -Wextra -O2 -fPIC
LDFLAGS  :=

# Directories
SRC_DIR  := src
INC_DIR  := include
OBJ_DIR  := obj
LIB_DIR  := lib

# wolfSSL (optional)
WOLFSSL_CFLAGS  := $(shell pkg-config --cflags wolfssl 2>/dev/null)
WOLFSSL_LDFLAGS := $(shell pkg-config --libs wolfssl 2>/dev/null)

# If wolfSSL found, enable it
ifneq ($(WOLFSSL_LDFLAGS),)
    CFLAGS  += $(WOLFSSL_CFLAGS) -DUSE_WOLFSSL
    LDFLAGS += $(WOLFSSL_LDFLAGS)
    TLS_ENABLED := yes
else
    TLS_ENABLED := no
endif

# Source files
SOURCES := $(wildcard $(SRC_DIR)/*.c)
OBJECTS := $(SOURCES:$(SRC_DIR)/%.c=$(OBJ_DIR)/%.o)

# Output library
LIBRARY := $(LIB_DIR)/libimmune_common.a

# === Targets ===

.PHONY: all clean info test

all: info $(LIBRARY)

info:
	@echo "========================================"
	@echo "  IMMUNE Common Library Build"
	@echo "========================================"
	@echo "  CC:          $(CC)"
	@echo "  CFLAGS:      $(CFLAGS)"
	@echo "  wolfSSL:     $(TLS_ENABLED)"
	@echo "========================================"

$(LIBRARY): $(OBJECTS) | $(LIB_DIR)
	@echo "[AR] $@"
	@ar rcs $@ $^

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	@echo "[CC] $<"
	@$(CC) $(CFLAGS) -I$(INC_DIR) -c $< -o $@

$(OBJ_DIR):
	@mkdir -p $@

$(LIB_DIR):
	@mkdir -p $@

# === Tests ===

test: $(LIBRARY)
	@echo "[TEST] Building TLS tests..."
	$(CC) $(CFLAGS) -I$(INC_DIR) \
		../tests/test_tls_transport.c \
		-L$(LIB_DIR) -limmune_common $(LDFLAGS) \
		-o ../tests/test_tls
	@echo "[RUN] Running tests..."
	@../tests/test_tls

# === Clean ===

clean:
	rm -rf $(OBJ_DIR) $(LIB_DIR)
	rm -f ../tests/test_tls

# === Install wolfSSL (helper) ===

install-wolfssl:
	@echo "Installing wolfSSL..."
	@pkg install wolfssl || (echo "Use: cd /usr/ports/security/wolfssl && make install")
