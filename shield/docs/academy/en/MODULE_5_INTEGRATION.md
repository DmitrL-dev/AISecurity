# SENTINEL Academy — Module 5

## Integration

_SSA Level | Duration: 4 hours_

---

## C Integration

### Basic Usage

```c
#include "sentinel_shield.h"

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);
    shield_load_config(&ctx, "config.json");

    // Evaluate input
    evaluation_result_t result;
    shield_evaluate(&ctx, user_input, strlen(user_input),
                    "external", DIRECTION_INBOUND, &result);

    if (result.action == ACTION_BLOCK) {
        printf("BLOCKED: %s\n", result.reason);
    } else {
        // Safe to process
        process_with_llm(user_input);
    }

    shield_destroy(&ctx);
    return 0;
}
```

---

## Python FFI

```python
from sentinel_shield import Shield

shield = Shield("config.json")

result = shield.evaluate(user_input, zone="external")
if result.blocked:
    return {"error": result.reason}
else:
    response = call_llm(user_input)
    return {"response": response}
```

---

## Go FFI

```go
import "github.com/sentinel/shield-go"

shield := shield.New("config.json")
defer shield.Close()

result := shield.Evaluate(userInput, "external", shield.INBOUND)
if result.Blocked {
    return fmt.Errorf("blocked: %s", result.Reason)
}
```

---

## REST API

```bash
# Evaluate
curl -X POST http://localhost:8080/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"input": "test", "zone": "external"}'

# Response
{
  "action": "allow",
  "score": 0.12,
  "latency_ms": 0.8
}
```

---

## Docker Sidecar

```yaml
version: "3.8"
services:
  app:
    image: your-app
    depends_on:
      - shield

  shield:
    image: sentinel/shield
    ports:
      - "8080:8080"
    volumes:
      - ./config.json:/etc/shield/config.json
```

---

## Next Module

**Module 5B: CLI Reference (194 commands)**

---

_"Integration is where Shield meets reality."_
