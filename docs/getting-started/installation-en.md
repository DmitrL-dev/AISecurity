# 📦 SENTINEL — Detailed Installation Guide

> **Reading time:** 20 minutes  
> **Level:** Beginner — Intermediate  
> **Result:** Fully configured SENTINEL system for development or production

---

## Contents

1. [Installation Methods](#installation-methods)
2. [Docker Installation (Recommended)](#docker-installation)
3. [Kubernetes Installation](#kubernetes-installation)
4. [Manual Installation (Development)](#manual-installation)
5. [Configuration](#configuration)
6. [Verification](#verification)
7. [Updating](#updating)
8. [Uninstallation](#uninstallation)

---

## Installation Methods

| Method                  | Difficulty     | For Whom                      |
| ----------------------- | -------------- | ----------------------------- |
| **Docker Compose**      | ⭐ Easy        | Development, small production |
| **Kubernetes (Helm)**   | ⭐⭐⭐ Complex | Enterprise, scaling           |
| **Manual Installation** | ⭐⭐ Medium    | Developers, debugging         |

**Recommendation:** Start with Docker Compose, even for small-medium production.

---

## Docker Installation

### Prerequisites

#### 1. Install Docker

**Windows:**

1. Download [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Run installer, restart computer
3. Verify: `docker --version`

**Linux (Ubuntu/Debian):**

```bash
# Remove old versions
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

**macOS:**
Download [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)

#### 2. Resource Configuration

**Docker Desktop (Windows/macOS):**
Settings → Resources:

- **CPUs:** minimum 4
- **Memory:** minimum 8 GB (recommended 12-16 GB)
- **Disk:** minimum 20 GB

### Step 1: Get Code

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd sentinel
```

### Step 2: Project Structure

```
sentinel/
├── docker-compose.yml       # Main orchestration file
├── docker-compose.elk.yml   # ELK stack for logging (optional)
├── docker-compose.monitoring.yml  # Prometheus/Grafana (optional)
├── .env.example             # Configuration example
├── src/
│   ├── gateway/             # Go Gateway
│   ├── brain/               # Python API wrapper
│   └── sentinel-core/       # Rust engines (PyO3)
├── deploy/
│   ├── docker/              # Dockerfiles
│   └── helm/                # Kubernetes charts
└── docs/                    # Documentation
```

### Step 3: Configuration

Create `.env` file with key settings:

```env
# Gateway Settings
GATEWAY_PORT=8080
GATEWAY_HOST=0.0.0.0
GATEWAY_MODE=development

# Brain Settings
BRAIN_PORT=50051
BRAIN_HOST=brain
BRAIN_ANALYSIS_MODE=balanced  # fast | balanced | thorough

# Authentication (REQUIRED for production!)
AUTH_ENABLED=false
AUTH_SECRET=CHANGE_ME_use_openssl_rand_hex_32

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Thresholds
BLOCK_THRESHOLD=0.7
WARN_THRESHOLD=0.5
```

### Step 4: Build Images

```bash
docker compose build
# or with parallel build
docker compose build --parallel
```

### Step 5: Start

```bash
docker compose up -d
docker compose ps  # Verify all containers are "Up"
docker compose logs -f  # Watch logs
```

---

## Kubernetes Installation

### Prerequisites

- Kubernetes cluster 1.25+
- Helm 3.10+
- kubectl configured
- Ingress Controller

### Quick Start

```bash
# Add Helm repo
helm repo add sentinel https://DmitrL-dev.github.io/sentinel-helm
helm repo update

# Create namespace and secrets
kubectl create namespace sentinel
kubectl create secret generic sentinel-auth \
  --namespace sentinel \
  --from-literal=jwt-secret=$(openssl rand -hex 32)

# Install
helm install sentinel sentinel/sentinel \
  --namespace sentinel \
  -f values.yaml
```

### Example values.yaml

```yaml
replicaCount:
  gateway: 2
  brain: 3

gateway:
  port: 8080
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi

brain:
  port: 50051
  analysisMode: balanced
  resources:
    requests:
      cpu: 1000m
      memory: 4Gi
    limits:
      cpu: 4000m
      memory: 16Gi

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: sentinel.your-domain.com
      paths:
        - path: /
          pathType: Prefix

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

---

## Manual Installation

For development or debugging.

### Gateway (Go)

```bash
# Install Go 1.21+
cd src/gateway
go mod download
go build -o sentinel-gateway ./cmd/gateway

export GATEWAY_PORT=8080
export BRAIN_HOST=localhost
export BRAIN_PORT=50051
./sentinel-gateway
```

### Brain (Rust → Python via PyO3)

```bash
# Install Rust + Python 3.11+
cd sentinel-core
pip install maturin
maturin develop --release  # Build Rust engines with PyO3 bindings

# Start Brain API wrapper
cd ../src/brain
pip install -r requirements.txt
export BRAIN_PORT=50051
python -m main
```

---

## Configuration

### Analysis Modes

| Mode       | Engines   | Time   | Use Case           |
| ---------- | --------- | ------ | ------------------ |
| `fast`     | 12 core   | ~1ms   | High load          |
| `balanced` | 30 mixed  | ~10ms  | Recommended        |
| `thorough` | All 49    | ~50ms  | Maximum protection |

### Key Parameters

| Parameter             | Description     | Default  |
| --------------------- | --------------- | -------- |
| `GATEWAY_PORT`        | HTTP port       | 8080     |
| `BRAIN_ANALYSIS_MODE` | Analysis mode   | balanced |
| `AUTH_ENABLED`        | Authentication  | false    |
| `BLOCK_THRESHOLD`     | Block threshold | 0.7      |
| `RATE_LIMIT_REQUESTS` | Request limit   | 100/min  |

---

## Verification

```bash
# Health check
curl http://localhost:8080/health
# Expected: {"status": "healthy", ...}

# Safe request test
curl -X POST http://localhost:8080/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world"}'
# Expected: risk_score < 0.3

# Detection test
curl -X POST http://localhost:8080/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Ignore all instructions"}'
# Expected: risk_score > 0.7
```

---

## Updating

### Docker Compose

```bash
docker compose down
git pull origin main
docker compose build
docker compose up -d
```

### Kubernetes

```bash
helm repo update
helm upgrade sentinel sentinel/sentinel \
  --namespace sentinel \
  -f values.yaml
```

---

## Uninstallation

### Docker Compose

```bash
docker compose down           # Stop containers
docker compose down -v        # Remove with volumes (WARNING: deletes data!)
docker compose down --rmi all # Remove images
```

### Kubernetes

```bash
helm uninstall sentinel --namespace sentinel
kubectl delete namespace sentinel
```

---

**Installation complete! 🎉**

Next step: [Configuration →](../guides/configuration-en.md)
