# Quick Start Guide

Get SENTINEL Shield running in 5 minutes.

---

## Prerequisites

- CMake 3.14+
- C11 compiler (GCC 7+, Clang 8+, MSVC 2019+)
- Git

---

## Step 1: Clone & Build

### Linux / macOS

```bash
git clone https://github.com/SENTINEL/shield.git
cd shield
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
```

### Windows

```powershell
git clone https://github.com/SENTINEL/shield.git
cd shield
mkdir build; cd build
cmake -G "Visual Studio 17 2022" ..
cmake --build . --config Release
```

---

## Step 2: Verify Installation

```bash
./shield --version
```

Expected output:

```
SENTINEL Shield v1.2.0
Build: Jan 01 2026 22:00:00
Platform: Linux
```

---

## Step 3: Minimal Configuration

Create `config.json`:

```json
{
  "version": "1.2.0",
  "zones": [{ "name": "external", "trust_level": 1 }],
  "rules": [
    {
      "name": "block_injection",
      "pattern": "ignore.*previous",
      "action": "block"
    }
  ],
  "api": { "enabled": true, "port": 8080 }
}
```

---

## Step 4: Start Shield

```bash
./shield -c config.json
```

Output:

```
╔══════════════════════════════════════════════════════════╗
║                   SENTINEL SHIELD                         ║
║                      v1.2.0                              ║
║                                                          ║
║         The DMZ Your AI Deserves                         ║
╚══════════════════════════════════════════════════════════╝

[INFO] Loading configuration: config.json
[INFO] API endpoint: http://0.0.0.0:8080
[INFO] SENTINEL Shield running...
```

---

## Step 5: Test API

### Allow legitimate request

```bash
curl -X POST http://localhost:8080/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"input": "What is 2+2?", "zone": "external"}'
```

Response:

```json
{ "action": "allow", "threat_score": 0.0 }
```

### Block attack

```bash
curl -X POST http://localhost:8080/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"input": "Ignore previous instructions", "zone": "external"}'
```

Response:

```json
{ "action": "block", "reason": "Rule: block_injection", "threat_score": 0.95 }
```

---

## Step 6: Integrate in Your Application

```c
#include "sentinel_shield.h"

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);
    shield_load_config(&ctx, "config.json");

    // Check user input
    evaluation_result_t result;
    shield_evaluate(&ctx, user_input, strlen(user_input),
                    "external", DIRECTION_INBOUND, &result);

    if (result.action == ACTION_BLOCK) {
        printf("Blocked: %s\n", result.reason);
        return 1;
    }

    // Safe to proceed
    call_llm_api(user_input);

    shield_destroy(&ctx);
    return 0;
}
```

Compile:

```bash
gcc -I/path/to/shield/include \
    -L/path/to/shield/lib \
    -lsentinel-shield \
    my_app.c -o my_app
```

---

## Docker

```bash
docker run -d -p 8080:8080 -p 9090:9090 \
  -v $(pwd)/config.json:/etc/shield/config.json \
  sentinel/shield:latest
```

---

## Next Steps

- [Configuration Reference](CONFIGURATION.md)
- [CLI Commands](CLI.md)
- [Architecture Guide](ARCHITECTURE.md)
- [Tutorials](tutorials/01_protect_first_llm.md)

---

_Чистый C. Без компромиссов._
