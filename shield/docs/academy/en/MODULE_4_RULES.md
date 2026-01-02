# SENTINEL Academy — Module 4

## Rules and Patterns

_SSA Level | Duration: 4 hours_

---

## Rule Engine

Shield uses ACL-style rules:

```
shield-rule <sequence> <action> <direction> <zone-type> [match ...]
```

### Actions

| Action | Description |
|--------|-------------|
| `permit` | Allow through |
| `deny` | Block |
| `log` | Allow and log |
| `alert` | Allow with alert |

### Directions

| Direction | Description |
|-----------|-------------|
| `inbound` | Incoming requests |
| `outbound` | AI responses |
| `any` | Both directions |

---

## Rule Examples

```
# Block injection attempts
shield-rule 10 deny inbound any match injection

# Block jailbreak
shield-rule 20 deny inbound any match jailbreak

# Log external requests
shield-rule 30 log inbound external

# Block PII in responses
shield-rule 40 deny outbound any match pii

# Default permit
shield-rule 100 permit any any
```

---

## Pattern Types

### Built-in Patterns

| Pattern | What it Matches |
|---------|-----------------|
| `injection` | Prompt injection attempts |
| `jailbreak` | Jailbreak patterns |
| `exfiltration` | Data extraction attempts |
| `pii` | Personal information |
| `secrets` | API keys, passwords |

### Custom Regex

```
shield-rule 50 deny inbound any match regex "ignore.*previous"
```

---

## Access Lists

Group rules into Access Lists:

```
access-list 100
  shield-rule 10 deny inbound any match injection
  shield-rule 20 deny inbound any match jailbreak
  shield-rule 100 permit any any

zone external
  apply access-list 100 inbound
```

---

## Evaluation Order

1. Rules evaluated in sequence order (10, 20, 30...)
2. First match determines action
3. Implicit deny if no match

---

## Next Module

**Module 5: Integration**

---

_"Rules are the foundation of security."_
