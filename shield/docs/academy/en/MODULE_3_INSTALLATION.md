# SENTINEL Academy — Module 3

## Installation

_SSA Level | Duration: 3 hours_

---

## Prerequisites

- C compiler (GCC, Clang, or MSVC)
- CMake 3.10+
- Make or Ninja

---

## Build from Source

### Linux/macOS

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community/shield

mkdir build && cd build
cmake ..
make -j$(nproc)
```

### Windows

```powershell
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity\sentinel-community\shield

mkdir build; cd build
cmake -G "Visual Studio 17 2022" ..
cmake --build . --config Release
```

---

## Docker

```bash
docker pull sentinel/shield:latest
docker run -d -p 8080:8080 sentinel/shield
```

---

## Configuration

### Basic config.json

```json
{
  "version": "1.2.0",
  "zones": [
    { "name": "external", "trust_level": 1 },
    { "name": "internal", "trust_level": 10 }
  ],
  "guards": ["llm", "rag", "agent", "tool", "mcp", "api"],
  "api": {
    "enabled": true,
    "port": 8080
  },
  "metrics": {
    "enabled": true,
    "port": 9090
  }
}
```

---

## Verify Installation

```bash
./shield --version
# SENTINEL Shield v1.2.0

./shield-cli
Shield> show version
Shield> show guards
Shield> exit
```

---

## Directory Structure

```
shield/
├── src/
│   ├── core/        # Engine core (42 files)
│   ├── cli/         # CLI (10 files, 194 commands)
│   ├── protocols/   # Protocols (20 files)
│   ├── guards/      # Guards (6 files)
│   └── ebpf/        # eBPF (3 files)
├── include/         # Headers (64 files)
├── tests/           # Unit tests
└── docs/            # Documentation
```

---

## Next Module

**Module 4: Rules and Patterns**

---

_"Installation is the beginning."_
