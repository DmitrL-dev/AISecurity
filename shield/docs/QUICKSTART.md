# Quick Start Guide

Get SENTINEL Shield running in 5 minutes.

---

## Prerequisites

- C11 compiler (GCC 7+, Clang 8+)
- Make (GNU Make)
- Git
- OpenSSL development libraries (optional, for TLS)

---

## Step 1: Clone & Build

### Linux / macOS

```bash
git clone https://github.com/SENTINEL/shield.git
cd shield
make clean && make
make test_all  # Verify 94 tests pass
```

### Windows (MSYS2/MinGW)

```bash
git clone https://github.com/SENTINEL/shield.git
cd shield
pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-openssl make
make clean && make
```

---

## Step 2: Verify Installation

```bash
make test_llm_mock
```

Expected output:

```
═══════════════════════════════════════════════════════════════
  Total Tests:  9
  Passed:       9
  Failed:       0
═══════════════════════════════════════════════════════════════
  ✅ ALL LLM INTEGRATION TESTS PASSED
═══════════════════════════════════════════════════════════════
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
gcc -Ipath/to/shield/include \
    -Lpath/to/shield/build \
    -lshield \
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
