#!/bin/sh
#
# SENTINEL IMMUNE — Install Script
#
# Installs IMMUNE Agent on DragonFlyBSD.
#
# Usage:
#   ./install.sh         # Full install
#   ./install.sh update  # Update only
#   ./install.sh remove  # Uninstall
#

set -e

PREFIX="/usr/local"
SYSCONFDIR="/etc/immune"
VARDIR="/var/immune"
LOGDIR="/var/log/immune"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    printf "${GREEN}[INFO]${NC} %s\n" "$1"
}

log_warn() {
    printf "${YELLOW}[WARN]${NC} %s\n" "$1"
}

log_error() {
    printf "${RED}[ERROR]${NC} %s\n" "$1"
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

check_system() {
    log_info "Checking system..."
    
    # Check OS
    if [ "$(uname)" != "DragonFly" ]; then
        log_warn "Not running on DragonFlyBSD, some features may not work"
    fi
    
    # Check dependencies
    for cmd in make nasm gcc; do
        if ! command -v $cmd > /dev/null 2>&1; then
            log_error "Missing dependency: $cmd"
            exit 1
        fi
    done
    
    log_info "System check passed"
}

create_directories() {
    log_info "Creating directories..."
    
    mkdir -p ${SYSCONFDIR}
    mkdir -p ${VARDIR}/memory
    mkdir -p ${LOGDIR}
    
    # Set permissions
    chmod 700 ${VARDIR}
    chmod 755 ${LOGDIR}
}

build_agent() {
    log_info "Building IMMUNE Agent..."
    
    cd "$(dirname "$0")/.."
    
    # Build userspace library
    make clean || true
    make all
    
    log_info "Agent built successfully"
}

build_kmod() {
    log_info "Building kernel module..."
    
    cd "$(dirname "$0")/.."
    
    make -f Makefile.kmod clean || true
    make -f Makefile.kmod
    
    log_info "Kernel module built"
}

install_files() {
    log_info "Installing files..."
    
    cd "$(dirname "$0")/.."
    
    # Install binaries
    install -m 755 immuned ${PREFIX}/sbin/
    install -m 755 libimmune.so ${PREFIX}/lib/
    
    # Install kernel module
    if [ -f immune.ko ]; then
        install -m 555 immune.ko /boot/modules/
    fi
    
    # Install config
    if [ ! -f ${SYSCONFDIR}/agent.conf ]; then
        install -m 600 scripts/agent.conf ${SYSCONFDIR}/
    else
        log_warn "Config exists, not overwriting"
    fi
    
    # Install RC script
    install -m 555 scripts/rc.d/immuned /etc/rc.d/
    
    # Install patterns
    install -m 644 ../patterns/*.dat ${SYSCONFDIR}/ 2>/dev/null || true
    
    log_info "Files installed"
}

enable_service() {
    log_info "Enabling service..."
    
    # Add to rc.conf
    if ! grep -q "immuned_enable" /etc/rc.conf 2>/dev/null; then
        echo 'immuned_enable="YES"' >> /etc/rc.conf
    fi
    
    log_info "Service enabled"
}

start_service() {
    log_info "Starting IMMUNE Agent..."
    
    service immuned start || /etc/rc.d/immuned start
    
    sleep 2
    
    if service immuned status > /dev/null 2>&1; then
        log_info "IMMUNE Agent is running"
    else
        log_warn "Agent may not have started correctly"
    fi
}

install_full() {
    log_info "===== SENTINEL IMMUNE Installation ====="
    
    check_root
    check_system
    create_directories
    build_agent
    build_kmod
    install_files
    enable_service
    start_service
    
    log_info "===== Installation Complete ====="
    echo ""
    echo "IMMUNE Agent installed successfully!"
    echo ""
    echo "Commands:"
    echo "  service immuned status   - Check status"
    echo "  service immuned restart  - Restart agent"
    echo "  kldload immune           - Load kernel module"
    echo ""
    echo "Config: ${SYSCONFDIR}/agent.conf"
    echo "Logs:   ${LOGDIR}/agent.log"
    echo ""
}

update_only() {
    log_info "===== SENTINEL IMMUNE Update ====="
    
    check_root
    
    # Stop service
    service immuned stop 2>/dev/null || true
    
    build_agent
    build_kmod
    install_files
    
    # Restart
    service immuned start
    
    log_info "===== Update Complete ====="
}

remove_all() {
    log_info "===== SENTINEL IMMUNE Removal ====="
    
    check_root
    
    # Stop service
    service immuned stop 2>/dev/null || true
    
    # Unload kernel module
    kldunload immune 2>/dev/null || true
    
    # Remove files
    rm -f ${PREFIX}/sbin/immuned
    rm -f ${PREFIX}/lib/libimmune.so
    rm -f /boot/modules/immune.ko
    rm -f /etc/rc.d/immuned
    
    # Keep config and data
    log_warn "Config and data preserved in ${SYSCONFDIR} and ${VARDIR}"
    
    # Remove from rc.conf
    sed -i '' '/immuned_enable/d' /etc/rc.conf 2>/dev/null || true
    
    log_info "===== Removal Complete ====="
}

# Main
case "${1:-install}" in
    install)
        install_full
        ;;
    update)
        update_only
        ;;
    remove|uninstall)
        remove_all
        ;;
    *)
        echo "Usage: $0 [install|update|remove]"
        exit 1
        ;;
esac
