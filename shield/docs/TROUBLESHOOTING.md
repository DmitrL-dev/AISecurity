# SENTINEL Shield Troubleshooting Guide

---

## Common Issues

### Shield Won't Start

**Symptom:** `shield: error: failed to start`

**Check:**

```bash
# Config validation
shield --validate-config /etc/shield/config.json

# Port in use
netstat -tlnp | grep 8080

# Permissions
ls -la /var/log/shield/
```

**Solutions:**

1. Fix config errors shown in validation
2. Change port or stop conflicting service
3. Create directories with proper permissions

---

### High CPU Usage

**Symptom:** Shield using >80% CPU

**Check:**

```bash
Shield> show metrics
Shield> debug on
```

**Common Causes:**

- Complex regex patterns
- Too many rules
- High request rate

**Solutions:**

1. Simplify regex patterns
2. Use signature-based matching
3. Enable rate limiting
4. Increase thread pool size

---

### Memory Growing

**Symptom:** Memory usage increasing over time

**Check:**

```bash
Shield> show sessions
Shield> show history
```

**Solutions:**

1. Configure session timeout
2. Limit history size
3. Enable memory pool limits:

```json
{
  "performance": {
    "memory_pool_blocks": 1024,
    "max_sessions": 10000
  }
}
```

---

### Requests Being Blocked Incorrectly

**Symptom:** Legitimate requests blocked (false positives)

**Debug:**

```bash
Shield> evaluate "the blocked text here"
Shield> show rules --verbose
```

**Solutions:**

1. Adjust rule patterns to be more specific
2. Lower severity threshold
3. Whitelist known-good patterns
4. Use zone trust levels

```json
{
  "rules": [
    {
      "name": "block_injection",
      "pattern": "^ignore\\s+(?:all\\s+)?previous",
      "case_insensitive": true,
      "action": "block"
    }
  ]
}
```

---

### Attacks Not Detected

**Symptom:** Known attacks getting through (false negatives)

**Check:**

```bash
Shield> show signatures
Shield> evaluate "attack payload here" --verbose
```

**Solutions:**

1. Update signature database
2. Enable semantic analysis
3. Add custom rules
4. Lower detection threshold

```json
{
  "semantic": {
    "enabled": true,
    "intent_threshold": 0.5
  }
}
```

---

### HA Failover Not Working

**Symptom:** Standby not taking over on primary failure

**Check:**

```bash
Shield> show ha status
Shield> show ha peers
```

**Common Causes:**

- Network connectivity between nodes
- Incorrect peer configuration
- Firewall blocking SHSP port

**Solutions:**

```bash
# Test connectivity
ping peer-address
telnet peer-address 5001

# Check firewall
iptables -L | grep 5001
```

---

### Metrics Not Showing

**Symptom:** Prometheus endpoint returns empty

**Check:**

```bash
curl http://localhost:9090/metrics
Shield> show metrics
```

**Solutions:**

1. Ensure metrics enabled in config
2. Check port binding
3. Verify no firewall blocking

---

### CLI Connection Refused

**Symptom:** Can't connect to CLI

**Check:**

```bash
netstat -tlnp | grep 2222
./shield-cli --debug
```

**Solutions:**

1. Ensure Shield is running
2. Check CLI port binding (default: 127.0.0.1)
3. For remote: bind to 0.0.0.0 or specific IP

---

## Debug Mode

Enable verbose logging:

```bash
# Command line
./shield --log-level debug

# Runtime
Shield> debug on

# Config
{
  "log_level": "debug"
}
```

---

## Log Locations

| Platform | Path                          |
| -------- | ----------------------------- |
| Linux    | `/var/log/shield/`            |
| macOS    | `/usr/local/var/log/shield/`  |
| Windows  | `C:\ProgramData\Shield\Logs\` |

---

## Build Issues

### Compilation Errors

**Symptom:** `make` fails

**Check:**

```bash
# Prerequisites
gcc --version   # >= 7.0
make --version  # any

# Rebuild clean
make clean && make
```

**Common Causes:**

- Missing compiler
- Old GCC version (< 7.0)
- Missing OpenSSL headers (for TLS)

**Solutions:**

```bash
# Ubuntu/Debian
apt install build-essential libssl-dev

# MSYS2/MinGW
pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-openssl make
```

---

### Test Failures

**Symptom:** Tests fail

**Check:**

```bash
make test_all 2>&1 | tail -20
```

**Solutions:**

1. Rebuild from clean
2. Check for missing test files
3. Verify test binary built correctly

```bash
make clean && make && make test_all
```

---

## Brain FFI Issues

### Brain Not Responding

**Symptom:** Brain analysis returns empty or errors

**Check:**

```bash
Shield> show brain
```

**Solutions:**

1. Verify Brain mode in config:

```json
{ "brain": { "mode": "stub" } }
```

2. For HTTP mode, check Brain service:

```bash
curl http://localhost:5000/health
```

---

## Getting Help

1. **Documentation:** docs/
2. **Community:** GitHub Discussions
3. **Academy:** docs/ACADEMY.md
4. **Issues:** https://github.com/SENTINEL/shield/issues

---

## See Also

- [Performance Tuning](PERFORMANCE.md)
- [Configuration](CONFIGURATION.md)
- [Deployment](DEPLOYMENT.md)

---

_"Every problem has a solution. We're small, but WE CAN help."_
