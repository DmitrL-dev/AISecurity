# Brain FFI — Implementation Plan

> **Priority:** P1  
> **Estimated Effort:** 4-5 days  
> **Goal:** Connect Python ML engines to C guards

---

## Overview

Create Foreign Function Interface (FFI) layer to connect:
- **Shield C Guards** → **Brain Python Engines**
- Enable 212 Python detection engines to power C-based guards

---

## Architecture Options

### Option 1: Embedded Python (Recommended)
```
┌─────────────────────────────────────────┐
│              Shield (C)                 │
│  ┌─────────────────────────────────────┤
│  │  Python Embedded Runtime            │
│  │  ├── Py_Initialize()                │
│  │  ├── PyImport_Import("sentinel")    │
│  │  └── PyObject_CallMethod(...)       │
│  │         │                           │
│  │         ▼                           │
│  │  ┌─────────────────────────────┐    │
│  │  │  Brain Python Engines       │    │
│  │  │  └── 212 detection engines  │    │
│  │  └─────────────────────────────┘    │
│  └─────────────────────────────────────┤
└─────────────────────────────────────────┘
```

**Pros:**
- Single process
- Low latency (<1ms overhead)
- Direct memory access

**Cons:**
- Requires Python dev headers
- GIL considerations

### Option 2: Subprocess/IPC
```
┌────────────────┐     ┌────────────────┐
│  Shield (C)    │────▶│  Brain (Python)│
│                │ IPC │                │
│  Unix Socket   │◀────│  212 engines   │
└────────────────┘     └────────────────┘
```

**Pros:**
- Process isolation
- Language independence

**Cons:**
- Higher latency (1-5ms)
- Serialization overhead

### Option 3: HTTP Client
```
Shield (C) ──HTTP──▶ Brain API (Python FastAPI)
```

**Pros:**
- Already exists (Brain has API)
- No new dependencies

**Cons:**
- Network latency
- Connection overhead

---

## Recommended: Option 1 + Option 3 Fallback

- **Primary:** Embedded Python for <1ms latency
- **Fallback:** HTTP to Brain API if Python unavailable

---

## File Structure

```
shield/
├── src/
│   └── ffi/                     # NEW: FFI module
│       ├── brain_ffi.c          # Main FFI implementation
│       ├── brain_ffi.h          # FFI interface
│       ├── python_bridge.c      # Python embedding
│       ├── python_bridge.h      # Python bridge interface
│       ├── http_client.c        # HTTP fallback client
│       └── http_client.h        # HTTP client interface
├── include/
│   └── shield_brain.h           # Public Brain integration API
└── bindings/
    └── python/
        └── shield_bridge.py     # Python side of bridge
```

---

## Implementation Phases

### Phase 1: Python Embedding Core (Day 1-2)
- [ ] `python_bridge.c` — Initialize Python runtime
- [ ] `python_bridge.h` — Bridge interface
- [ ] CMake/Makefile Python detection
- [ ] Basic call: C → Python function → C

### Phase 2: Brain Engine Wrapper (Day 2-3)
- [ ] `brain_ffi.c` — High-level engine interface
- [ ] `shield_bridge.py` — Python wrapper for engines
- [ ] Engine registry (load/unload engines)
- [ ] Async engine calls with timeout

### Phase 3: Guard Integration (Day 3-4)
- [ ] Connect LLM Guard → Brain injection engines
- [ ] Connect RAG Guard → Brain RAG engines
- [ ] Connect Agent Guard → Brain agent engines
- [ ] Result type mapping (Python dict → C struct)

### Phase 4: HTTP Fallback (Day 4-5)
- [ ] `http_client.c` — Simple HTTP client
- [ ] Brain API integration
- [ ] Automatic fallback logic
- [ ] Connection pooling

---

## API Design

### C Interface

```c
/* shield_brain.h */

typedef enum {
    BRAIN_ENGINE_INJECTION,
    BRAIN_ENGINE_JAILBREAK,
    BRAIN_ENGINE_RAG_POISONING,
    BRAIN_ENGINE_AGENT_MANIPULATION,
    BRAIN_ENGINE_ALL
} brain_engine_t;

typedef struct {
    bool detected;
    double confidence;
    const char *reason;
    const char *engine_name;
    double latency_ms;
} brain_result_t;

/* Initialize Brain FFI */
int brain_ffi_init(const char *python_home);

/* Shutdown Brain FFI */
void brain_ffi_shutdown(void);

/* Analyze with specific engine */
int brain_analyze(
    const char *input,
    brain_engine_t engine,
    brain_result_t *result
);

/* Analyze with all engines */
int brain_analyze_all(
    const char *input,
    brain_result_t *results,
    size_t *result_count
);

/* Check if Python available */
bool brain_python_available(void);

/* Get engine count */
size_t brain_engine_count(void);
```

### Python Bridge

```python
# shield_bridge.py

from sentinel.brain import Brain
from sentinel.brain.engines import get_all_engines

class ShieldBridge:
    """Bridge between C Shield and Python Brain"""
    
    def __init__(self):
        self.brain = Brain()
        self.engines = get_all_engines()
    
    def analyze(self, input_text: str, engine_name: str = None) -> dict:
        """Analyze input with specified engine or all engines"""
        if engine_name:
            engine = self.engines.get(engine_name)
            if engine:
                result = engine.analyze(input_text)
                return {
                    'detected': result.is_threat,
                    'confidence': result.confidence,
                    'reason': result.reason,
                    'engine': engine_name
                }
        else:
            # Run all engines
            results = self.brain.analyze(input_text)
            return results.to_dict()
    
    def get_engine_names(self) -> list:
        """Return list of available engine names"""
        return list(self.engines.keys())

# Global instance for C calls
_bridge = None

def init():
    global _bridge
    _bridge = ShieldBridge()
    return True

def analyze(input_text, engine_name=None):
    return _bridge.analyze(input_text, engine_name)

def get_engines():
    return _bridge.get_engine_names()
```

---

## Code Snippets

### python_bridge.h

```c
#ifndef SHIELD_PYTHON_BRIDGE_H
#define SHIELD_PYTHON_BRIDGE_H

#include <stdbool.h>

/* Initialize Python interpreter */
int python_bridge_init(const char *python_home);

/* Shutdown Python interpreter */
void python_bridge_shutdown(void);

/* Check if Python is available */
bool python_bridge_available(void);

/* Call Python function with string arg, get dict result */
int python_bridge_call(
    const char *module,
    const char *function,
    const char *arg,
    char **result_json,   /* Caller must free */
    char **error_msg      /* Caller must free */
);

#endif
```

### python_bridge.c (core)

```c
#include "ffi/python_bridge.h"
#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bool g_initialized = false;

int python_bridge_init(const char *python_home) {
    if (g_initialized) return 0;
    
    if (python_home) {
        Py_SetPythonHome(Py_DecodeLocale(python_home, NULL));
    }
    
    Py_Initialize();
    
    if (!Py_IsInitialized()) {
        fprintf(stderr, "[FFI] Failed to initialize Python\n");
        return -1;
    }
    
    /* Add sentinel to path */
    PyRun_SimpleString(
        "import sys\n"
        "sys.path.insert(0, '../src')\n"
    );
    
    /* Import shield bridge */
    PyObject *bridge = PyImport_ImportModule("shield_bridge");
    if (!bridge) {
        PyErr_Print();
        return -1;
    }
    
    /* Call init() */
    PyObject *init_result = PyObject_CallMethod(bridge, "init", NULL);
    Py_XDECREF(init_result);
    Py_DECREF(bridge);
    
    g_initialized = true;
    printf("[FFI] Python bridge initialized\n");
    
    return 0;
}

void python_bridge_shutdown(void) {
    if (g_initialized) {
        Py_Finalize();
        g_initialized = false;
    }
}

bool python_bridge_available(void) {
    return g_initialized && Py_IsInitialized();
}
```

---

## Build Integration

### CMakeLists.txt additions

```cmake
# Find Python
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# Add FFI sources
set(FFI_SOURCES
    src/ffi/brain_ffi.c
    src/ffi/python_bridge.c
    src/ffi/http_client.c
)

# Link Python
target_include_directories(shield PRIVATE ${Python3_INCLUDE_DIRS})
target_link_libraries(shield ${Python3_LIBRARIES})
```

### Makefile additions

```makefile
# Python flags
PYTHON_CFLAGS := $(shell python3-config --cflags)
PYTHON_LDFLAGS := $(shell python3-config --ldflags --embed)

# FFI objects
FFI_OBJS := $(BUILD_DIR)/brain_ffi.o \
            $(BUILD_DIR)/python_bridge.o \
            $(BUILD_DIR)/http_client.o

# FFI target
$(BUILD_DIR)/%.o: src/ffi/%.c
	$(CC) $(CFLAGS) $(PYTHON_CFLAGS) -c $< -o $@
```

---

## Testing Plan

1. **Unit Tests:**
   - `test_python_bridge.c` — Python initialization
   - `test_brain_ffi.c` — Engine calls

2. **Integration Tests:**
   - E2E: C Guard → Python Engine → Result
   - Latency benchmarks

3. **Failure Modes:**
   - Python not installed → HTTP fallback
   - Engine timeout → Default deny
   - Memory pressure → Graceful degradation

---

## Success Criteria

- [ ] Python bridge initializes without errors
- [ ] Can call Brain engines from C
- [ ] Latency overhead < 1ms
- [ ] HTTP fallback works when Python unavailable
- [ ] All 6 guards connected to Brain engines

---

## Dependencies

- Python 3.9+ with dev headers
- sentinel Python package installed
- Optional: libcurl for HTTP fallback

---

## Next Steps After Brain FFI

1. **Real Guard Logic** — Replace stubs with Brain calls
2. **Engine Selection** — Dynamic engine selection per guard
3. **Caching** — Cache engine results for repeated inputs
4. **Metrics** — Brain call latency tracking
