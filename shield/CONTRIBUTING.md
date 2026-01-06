# Contributing to SENTINEL Shield

Thank you for your interest in contributing to SENTINEL Shield!

## Development Setup

### Prerequisites

- GCC 7+ or Clang 8+ (Linux/macOS)
- GNU Make
- OpenSSL development libraries (optional, for TLS)
- Valgrind (optional, for memory testing)
- Docker (optional)

### Building

```bash
# Clone and build
git clone https://github.com/SENTINEL/shield.git
cd shield
make clean && make

# Run tests
make test_all        # 94 CLI tests
make test_llm_mock   # 9 LLM integration tests

# With Valgrind
make test_valgrind

# With AddressSanitizer (Linux only)
make ASAN=1
```

### Windows (MSYS2/MinGW)

```bash
pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-openssl make
make clean && make
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
4. Ensure all tests pass: `make test_all && make test_llm_mock`
5. Ensure 0 warnings: `make clean && make`
6. Update documentation if needed
7. Submit PR with clear description

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
# All CLI tests (94)
make test_all

# LLM integration tests (9)
make test_llm_mock

# Memory leak check
make test_valgrind

# Total: 103 tests must pass
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
