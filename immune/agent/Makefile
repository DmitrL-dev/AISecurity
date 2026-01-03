#
# SENTINEL IMMUNE — Agent Makefile
#
# Builds userspace agent and kernel module
#

CC = cc
NASM = nasm
CFLAGS = -Wall -Wextra -O2 -fPIC -I./include
LDFLAGS = -lpthread

# OpenSSL (optional, for crypto)
CRYPTO_CFLAGS = $(shell pkg-config --cflags openssl 2>/dev/null || echo "")
CRYPTO_LDFLAGS = $(shell pkg-config --libs openssl 2>/dev/null || echo "-lssl -lcrypto")

# Directories
SRCDIR = src
INCDIR = include
BINDIR = bin
OBJDIR = obj
TESTDIR = tests
KMODDIR = kmod

# Sources
SRCS = $(wildcard $(SRCDIR)/*.c)
OBJS = $(patsubst $(SRCDIR)/%.c,$(OBJDIR)/%.o,$(SRCS))

# ASM Sources
ASM_SRCS = $(wildcard $(SRCDIR)/*.asm)
ASM_OBJS = $(patsubst $(SRCDIR)/%.asm,$(OBJDIR)/%.o,$(ASM_SRCS))

# Targets
TARGET = $(BINDIR)/immuned
TEST_TARGET = $(BINDIR)/test_agent

# Default target
all: dirs $(TARGET)

# Create directories
dirs:
	@mkdir -p $(BINDIR) $(OBJDIR)

# Main agent binary
$(TARGET): $(OBJS) $(ASM_OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS) $(CRYPTO_LDFLAGS)
	@echo "Built: $@"

# C objects
$(OBJDIR)/%.o: $(SRCDIR)/%.c
	$(CC) $(CFLAGS) $(CRYPTO_CFLAGS) -c -o $@ $<

# Assembly objects (NASM)
$(OBJDIR)/%.o: $(SRCDIR)/%.asm
	$(NASM) -f elf64 -o $@ $<

# ==================== Tests ====================

test: dirs test_binary
	./$(TEST_TARGET)

test_binary: $(TESTDIR)/test_agent.c $(filter-out $(OBJDIR)/daemon.o,$(OBJS))
	$(CC) $(CFLAGS) -o $(TEST_TARGET) $^ $(LDFLAGS) $(CRYPTO_LDFLAGS)
	@echo "Built: $(TEST_TARGET)"

# ==================== Kernel Module ====================

.PHONY: kmod
kmod:
	@echo "Building kernel module (DragonFlyBSD only)..."
ifeq ($(shell uname -s),DragonFly)
	cd $(KMODDIR) && make
else
	@echo "Kernel module requires DragonFlyBSD. Skipping."
endif

# ==================== Install ====================

PREFIX ?= /usr/local
SYSCONFDIR ?= /etc

install: $(TARGET)
	install -d $(DESTDIR)$(PREFIX)/sbin
	install -d $(DESTDIR)$(SYSCONFDIR)/immune
	install -m 755 $(TARGET) $(DESTDIR)$(PREFIX)/sbin/immuned
	install -m 644 conf/agent.conf $(DESTDIR)$(SYSCONFDIR)/immune/agent.conf
	@echo "Installed to $(DESTDIR)$(PREFIX)/sbin/immuned"

uninstall:
	rm -f $(DESTDIR)$(PREFIX)/sbin/immuned
	rm -rf $(DESTDIR)$(SYSCONFDIR)/immune
	@echo "Uninstalled"

# ==================== Clean ====================

clean:
	rm -rf $(OBJDIR) $(BINDIR)
	@echo "Cleaned"

.PHONY: all dirs test test_binary kmod install uninstall clean
