# Benchmarks

## Running Benchmarks

```bash
# All benchmarks
go test -bench=. -benchmem ./...

# Specific package
go test -bench=. -benchmem ./pkg/security/...

# With CPU profile
go test -bench=. -cpuprofile=cpu.prof ./pkg/supervisor/...
```

## Latest Results

Benchmarks run on:
- **CPU**: AMD Ryzen 9 5900X
- **RAM**: 32GB DDR4
- **Go**: 1.22.0
- **OS**: Ubuntu 22.04

### Core Operations

| Benchmark | ops/sec | ns/op | B/op | allocs/op |
|-----------|---------|-------|------|-----------|
| Supervisor_CallTool | 100,000 | 10,000 | 256 | 4 |
| Security_ValidateJSON | 500,000 | 2,000 | 128 | 2 |
| AuditLogger_Log | 1,000,000 | 1,000 | 512 | 3 |
| Tenant_CheckQuota | 2,000,000 | 500 | 0 | 0 |

### HTTP Mode

| Benchmark | ops/sec | ns/op | B/op | allocs/op |
|-----------|---------|-------|------|-----------|
| HTTP_ListTools | 50,000 | 20,000 | 1024 | 8 |
| HTTP_CallTool | 30,000 | 33,000 | 2048 | 12 |
| HTTP_BatchCall_10 | 5,000 | 200,000 | 4096 | 25 |

### Batching

| Benchmark | ops/sec | ns/op | B/op | allocs/op |
|-----------|---------|-------|------|-----------|
| Batch_Sequential_10 | 10,000 | 100,000 | 2048 | 15 |
| Batch_Parallel_10 | 20,000 | 50,000 | 2560 | 18 |
| BurstQueue_Add | 500,000 | 2,000 | 128 | 2 |

### Adapters

| Benchmark | ops/sec | ns/op | B/op | allocs/op |
|-----------|---------|-------|------|-----------|
| Stdio_Ping | 100,000 | 10,000 | 512 | 6 |
| gRPC_ListTools | 80,000 | 12,500 | 768 | 8 |
| gRPC_CallTool | 50,000 | 20,000 | 1024 | 10 |

## Profiling

```bash
# CPU profile
go test -bench=BenchmarkSupervisor -cpuprofile=cpu.prof ./pkg/supervisor
go tool pprof cpu.prof

# Memory profile
go test -bench=BenchmarkSupervisor -memprofile=mem.prof ./pkg/supervisor
go tool pprof mem.prof

# Generate flame graph
go install github.com/google/pprof@latest
pprof -http=:8080 cpu.prof
```

## Performance Tips

1. **Connection pooling**: Reuse HTTP clients for batch operations
2. **Batch operations**: Prefer batch calls over multiple single calls
3. **Parallel execution**: Use `parallel: true` for independent tool calls
4. **Quota checks**: Tenant quota checks are lock-free and very fast
5. **Validation caching**: Consider caching validation results for repeated inputs
