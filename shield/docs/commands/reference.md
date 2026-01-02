# SENTINEL Shield Command Reference

## Exec Mode Commands

### enable

Enter privileged EXEC mode.

```
sentinel> enable
sentinel#
```

### disable

Exit privileged EXEC mode.

```
sentinel# disable
sentinel>
```

### config

Enter global configuration mode.

```
sentinel# config
sentinel(config)#
```

### show zones

Display configured zones.

```
sentinel# show zones
Name                 Type       Provider        In-ACL   Out-ACL  Status
--------------------------------------------------------------------------------
openai-gpt4          llm        openai          100      200      active
pinecone             rag        -               -        -        active

Total: 2 zone(s)
```

### show rules [number]

Display shield rules.

```
sentinel# show rules 100
shield-rule 100:
     10 block input llm pattern "ignore.*instructions" (423 matches)
     20 block input llm entropy-high (17 matches)
```

### show stats

Display statistics.

```
sentinel# show stats
Shield Statistics:
------------------
Total requests:     10877
  Input:            5432
  Output:           5445
Blocked:            445 (4.1%)
Allowed:            10432 (95.9%)
```

### show version

Display version information.

```
sentinel# show version
SENTINEL Shield v1.0.0
Copyright (c) 2026 SENTINEL Project
```

---

## Config Mode Commands

### zone

Configure or create a zone.

```
sentinel(config)# zone openai-gpt4
sentinel(config-zone)#
```

### shield-rule

Add a shield rule.

```
sentinel(config)# shield-rule 10 block input llm pattern "ignore.*instructions"
sentinel(config)# shield-rule 20 block input llm entropy-high
sentinel(config)# shield-rule 100 quarantine output llm contains "password"
```

**Syntax:**

```
shield-rule <number> <action> <direction> <zone-type> [match-type] [pattern]
```

**Parameters:**

- `number`: Rule sequence (1-65535)
- `action`: block, allow, quarantine, analyze, log
- `direction`: input, output
- `zone-type`: llm, rag, agent, tool, mcp, any
- `match-type`: pattern, contains, entropy-high, sql-injection, jailbreak

### apply zone

Apply ACLs to a zone.

```
sentinel(config)# apply zone openai-gpt4 in 100 out 200
Applied to zone openai-gpt4: in=100, out=200
```

### write memory

Save configuration.

```
sentinel(config)# write memory
Building configuration...
[OK]
```

---

## Zone Mode Commands

### type

Set zone type.

```
sentinel(config-zone)# type llm
```

### provider

Set zone provider.

```
sentinel(config-zone)# provider openai
```

### description

Set zone description.

```
sentinel(config-zone)# description "Production GPT-4 API"
```

### exit

Exit zone configuration mode.

```
sentinel(config-zone)# exit
sentinel(config)#
```

---

## Example Configuration

```
! SENTINEL Shield Configuration

hostname sentinel

zone openai-gpt4
  type llm
  provider openai
  description "Production GPT-4 API"
!
zone pinecone
  type rag
  provider pinecone
!
shield-rule 10 block input llm pattern "ignore.*instructions"
shield-rule 20 block input llm pattern "disregard.*previous"
shield-rule 30 block input llm entropy-high
shield-rule 100 quarantine output llm contains "password"
shield-rule 110 quarantine output llm contains "api_key"
!
apply zone openai-gpt4 in 100 out 100
apply zone pinecone in 100 out 100
!
end
```
