#!/bin/bash
# ============================================================================
# SENTINEL AI Security Platform — Installation Script
# ============================================================================
# Usage: curl -sSL https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/install.sh | bash
#
# This script will:
#   1. Check prerequisites (Docker, Docker Compose)
#   2. Clone the repository
#   3. Create default configuration
#   4. Start all 5 services
#   5. Verify installation
#
# Modes:
#   --lite     Brain only (Python, no Docker)
#   --full     Full stack (Docker required)
#   --immune   IMMUNE EDR (DragonFlyBSD/FreeBSD)
#   --dev      Development mode
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/DmitrL-dev/AISecurity.git"
INSTALL_DIR="${SENTINEL_INSTALL_DIR:-$HOME/sentinel}"
BRANCH="${SENTINEL_BRANCH:-main}"
MODE="full"  # lite, full, immune, dev

# Parse arguments
for arg in "$@"; do
    case $arg in
        --lite)    MODE="lite" ;;
        --full)    MODE="full" ;;
        --immune)  MODE="immune" ;;
        --dev)     MODE="dev" ;;
        --help|-h) print_help; exit 0 ;;
    esac
done

# ============================================================================
# Functions
# ============================================================================

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║   ███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗ ║"
    echo "║   ██╔════╝██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║ ║"
    echo "║   ███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║ ║"
    echo "║   ╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║ ║"
    echo "║   ███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗"
    echo "║   ╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝"
    echo "║                                                               ║"
    echo "║           AI Defense & Red Team Platform                      ║"
    echo "║          209 Detection Engines | Strange Math™                ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_help() {
    echo "SENTINEL AI Security Platform — Installer"
    echo ""
    echo "Usage: ./install.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --lite     Python only, no Docker (pip install)"
    echo "  --full     Full stack with Docker (default)"
    echo "  --immune   IMMUNE EDR for BSD systems"
    echo "  --dev      Development mode with hot reload"
    echo "  --help     Show this help"
    echo ""
    echo "Examples:"
    echo "  curl -sSL https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/install.sh | bash"
    echo "  curl -sSL https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/install.sh | bash -s -- --lite"
    echo ""
}

install_lite() {
    log_step "Installing SENTINEL Lite (Python only)..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3.8+ is required. Install from: https://python.org"
        exit 1
    fi
    
    python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    log_info "Python version: $python_version"
    
    # Create virtual environment
    log_info "Creating virtual environment..."
    python3 -m venv "$INSTALL_DIR/venv"
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Install from PyPI
    log_info "Installing sentinel-llm-security..."
    pip install --upgrade pip
    pip install sentinel-llm-security
    
    # Download signatures
    log_info "Downloading threat signatures..."
    mkdir -p "$INSTALL_DIR/signatures"
    curl -sSL "https://cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@main/sentinel-community/signatures/jailbreaks-manifest.json" \
        -o "$INSTALL_DIR/signatures/manifest.json"
    
    # Create simple config
    cat > "$INSTALL_DIR/config.yaml" << EOF
# SENTINEL Lite Configuration
engines:
  enabled: all
  log_level: INFO

signatures:
  path: $INSTALL_DIR/signatures
  auto_update: true
EOF
    
    log_info "SENTINEL Lite installed successfully!"
    echo ""
    echo -e "${GREEN}Quick start:${NC}"
    echo "  source $INSTALL_DIR/venv/bin/activate"
    echo "  python -c \"from sentinel import analyze; print(analyze('test'))\""
    echo ""
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        return 1
    fi
    return 0
}

generate_secret() {
    openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p
}

# ============================================================================
# Prerequisites Check
# ============================================================================

check_prerequisites() {
    log_step "Checking prerequisites..."
    
    # Docker
    if ! check_command docker; then
        log_error "Docker is required. Install from: https://docs.docker.com/get-docker/"
        exit 1
    fi
    docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
    log_info "Docker version: $docker_version"
    
    # Docker Compose
    if ! docker compose version &> /dev/null; then
        if ! check_command docker-compose; then
            log_error "Docker Compose is required. Install from: https://docs.docker.com/compose/install/"
            exit 1
        fi
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi
    log_info "Docker Compose: OK"
    
    # Git
    if ! check_command git; then
        log_error "Git is required. Install from: https://git-scm.com/"
        exit 1
    fi
    log_info "Git: OK"
    
    # Check memory
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        total_mem=$(free -g | awk '/^Mem:/{print $2}')
        if [[ $total_mem -lt 4 ]]; then
            log_warn "System has ${total_mem}GB RAM. Recommended: 8GB+"
        else
            log_info "Memory: ${total_mem}GB"
        fi
    fi
    
    echo ""
    log_info "All prerequisites satisfied ✓"
}

# ============================================================================
# Installation
# ============================================================================

clone_repository() {
    log_step "Cloning SENTINEL repository..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        log_warn "Directory $INSTALL_DIR already exists"
        read -p "Overwrite? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing installation"
            return
        fi
        rm -rf "$INSTALL_DIR"
    fi
    
    git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
    log_info "Cloned to $INSTALL_DIR"
}

configure_environment() {
    log_step "Configuring environment..."
    
    cd "$INSTALL_DIR/sentinel-community"
    
    if [[ -f ".env" ]]; then
        log_warn ".env already exists, creating backup"
        cp .env .env.backup
    fi
    
    # Generate secrets
    API_KEY=$(generate_secret)
    SESSION_SECRET=$(generate_secret)
    ADMIN_PASSWORD=$(head -c 12 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 16)
    
    # Create .env from template
    cp .env.example .env
    
    # Set generated values
    sed -i "s/your-api-key-here/$API_KEY/" .env
    sed -i "s/your-session-secret-here/$SESSION_SECRET/" .env
    sed -i "s/change_me_immediately/$ADMIN_PASSWORD/" .env
    sed -i "s/sentinel_secure_password_change_me/$(generate_secret | head -c 32)/" .env
    
    log_info "Generated secure credentials"
    echo ""
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  IMPORTANT: Save these credentials!                   ║${NC}"
    echo -e "${YELLOW}╠═══════════════════════════════════════════════════════╣${NC}"
    echo -e "${YELLOW}║${NC}  Dashboard URL:  http://localhost:3000                ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  Username:       admin                                ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  Password:       $ADMIN_PASSWORD                      ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  API Key:        ${API_KEY:0:16}...                       ${YELLOW}║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
}

start_services() {
    log_step "Starting SENTINEL services..."
    
    cd "$INSTALL_DIR/sentinel-community"
    
    # Pull images first
    $COMPOSE_CMD -f docker-compose.full.yml pull 2>/dev/null || true
    
    # Build and start
    $COMPOSE_CMD -f docker-compose.full.yml up -d --build
    
    log_info "Services starting..."
}

wait_for_health() {
    log_step "Waiting for services to be healthy..."
    
    max_attempts=30
    attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -s http://localhost:8080/health > /dev/null 2>&1; then
            log_info "Gateway is healthy ✓"
            break
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    echo ""
    
    if [[ $attempt -eq $max_attempts ]]; then
        log_warn "Services may still be starting. Check logs with:"
        echo "  cd $INSTALL_DIR/sentinel-community"
        echo "  docker compose -f docker-compose.full.yml logs -f"
    fi
}

print_success() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                       ║${NC}"
    echo -e "${GREEN}║   🎉 SENTINEL installed successfully!                 ║${NC}"
    echo -e "${GREEN}║                                                       ║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}                                                       ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   Dashboard:    http://localhost:3000                 ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   API:          http://localhost:8080                 ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   API (HTTPS):  https://localhost:8443                ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                       ${GREEN}║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}                                                       ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   Useful commands:                                    ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   • View logs:    docker compose logs -f              ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   • Stop:         docker compose down                 ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   • Status:       docker compose ps                   ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                       ${GREEN}║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "📚 Documentation: https://dmitrl-dev.github.io/AISecurity/"
    echo "⭐ Star us on GitHub: https://github.com/DmitrL-dev/AISecurity"
    echo ""
}

# ============================================================================
# Main
# ============================================================================

main() {
    print_banner
    
    echo "This script will install SENTINEL AI Security Platform."
    echo "Installation directory: $INSTALL_DIR"
    echo "Mode: $MODE"
    echo ""
    
    # Interactive mode check
    if [[ -t 0 ]]; then
        read -p "Continue? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            log_info "Installation cancelled"
            exit 0
        fi
    fi
    
    case $MODE in
        lite)
            install_lite
            ;;
        full)
            check_prerequisites
            clone_repository
            configure_environment
            start_services
            wait_for_health
            print_success
            ;;
        immune)
            log_step "Installing IMMUNE EDR..."
            check_command cc || { log_error "C compiler required"; exit 1; }
            clone_repository
            cd "$INSTALL_DIR/sentinel-community/immune"
            log_info "Building Hive..."
            cd hive && ./build.sh && cd ..
            log_info "IMMUNE Hive built. See immune/README.md for Kmod instructions."
            ;;
        dev)
            check_prerequisites
            clone_repository
            cd "$INSTALL_DIR/sentinel-community"
            log_info "Installing Python dev dependencies..."
            pip install -e ".[dev]" 2>/dev/null || pip install -r requirements.txt
            log_info "Development environment ready!"
            echo "  cd $INSTALL_DIR/sentinel-community"
            echo "  python -m pytest tests/"
            ;;
    esac
}

# Run main
main "$@"
