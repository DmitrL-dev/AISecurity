# Contributing to SENTINEL Shield

Thank you for your interest in contributing to SENTINEL Shield!

## Development Setup

### Prerequisites

- GCC 9+ or Clang 10+ (Linux/macOS)
- MSVC 2019+ (Windows)
- CMake 3.16+
- Python 3.8+ (for testing)
- Docker (optional)

### Building

```bash
# Linux/macOS
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build

# Windows
cmake -B build -G "Visual Studio 16 2019"
cmake --build build --config Debug

# Run tests
cd build && ctest --output-on-failure
```

## Code Style

### C Code

- **Indent**: 4 spaces
- **Braces**: K&R style
- **Naming**:
  - Functions: `snake_case`
  - Types: `snake_case_t`
  - Macros: `UPPER_CASE`
  - Enums: `UPPER_CASE`
- **Comments**: `/* */` for multi-line, `//` for single line
- **Line length**: 100 characters max

Example:

```c
shield_err_t zone_create(zone_registry_t *reg, const char *name,
                          zone_type_t type, zone_t **out_zone)
{
    if (!reg || !name || !out_zone) {
        return SHIELD_ERR_INVALID;
    }

    zone_t *zone = calloc(1, sizeof(zone_t));
    if (!zone) {
        return SHIELD_ERR_NOMEM;
    }

    strncpy(zone->name, name, sizeof(zone->name) - 1);
    zone->type = type;

    *out_zone = zone;
    return SHIELD_OK;
}
```

### Headers

- Include guards: `#ifndef SHIELD_<MODULE>_H`
- Forward declarations where possible
- Document public API with comments

### Memory

- Always check malloc/calloc returns
- Use strncpy, snprintf (never strcpy, sprintf)
- Free in reverse order of allocation
- Use memory pools for hot paths

## Pull Request Process

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Write tests for new functionality
4. Ensure all tests pass: `ctest`
5. Update documentation if needed
6. Submit PR with clear description

## Testing

### Unit Tests

```c
// tests/test_feature.c
TEST(my_feature)
{
    ASSERT(my_function() == expected);
}
```

### Running Tests

```bash
# All tests
ctest

# Specific test
./build/test_core

# Benchmarks
./build/bench_core
```

## Reporting Issues

Please include:

- Shield version
- OS and compiler version
- Minimal reproduction steps
- Expected vs actual behavior

## Security Issues

For security vulnerabilities, see [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
