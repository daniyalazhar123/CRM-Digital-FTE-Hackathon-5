# Contributing to CRM Digital FTE

## Development Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Start Docker: `docker-compose up -d`
4. Run tests: `python -m pytest tests/ -v`

## Code Style

- **Python**: PEP 8
- **Docstrings**: Google style
- **Type hints**: Required for all functions
- **Line length**: 120 characters max

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for new functionality
4. Ensure all tests pass
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Testing

- All PRs must have tests
- Tests must pass CI/CD pipeline
- Minimum test coverage: 80%
- Run full test suite before submitting: `python -m pytest tests/ -v`

## Commit Messages

Follow conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `ci:` - CI/CD changes

## Architecture

See [README.md](README.md) for system architecture and design.
