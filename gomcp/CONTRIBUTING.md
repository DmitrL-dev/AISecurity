# Contributing to GoMCP

Thank you for your interest in contributing to GoMCP!

## Development Setup

```bash
# Clone
git clone https://github.com/sentinel-community/gomcp
cd gomcp

# Build
go build ./...

# Test
go test ./... -v

# Lint
go vet ./...
go fmt ./...
```

## Pull Request Guidelines

1. **Tests required** - All new code must have tests
2. **go vet clean** - No warnings from `go vet ./...`
3. **go fmt** - Run `go fmt ./...` before committing
4. **Documentation** - Update README if adding features

## Code Style

- Follow standard Go conventions
- Use meaningful variable names
- Comment exported functions
- Keep functions small and focused

## Reporting Issues

- Check existing issues first
- Include Go version (`go version`)
- Include OS and architecture
- Provide minimal reproduction steps

## License

By contributing, you agree that your contributions will be licensed under Apache 2.0.
