# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: Yes |

## Reporting a Vulnerability

If you discover a security vulnerability, please email: **security@techcorp.ai**

- We will respond within 48 hours
- Security issues will be patched within 7 days
- Please do not publicly disclose vulnerabilities until a patch is available

## Security Features

### Environment Variables
- All secrets stored in environment variables
- No hardcoded credentials in codebase
- `.env.example` provided for configuration reference
- `.gitignore` prevents accidental secret commits

### Input Validation
- All API endpoints validate input using Pydantic models
- SQL injection prevention via parameterized queries
- Email validation on all customer-facing endpoints
- Phone number format validation

### Database Security
- Parameterized SQL queries (no string concatenation)
- Connection pooling with limits (max 50 connections)
- Role-based access control ready

### API Security
- CORS middleware configured for web form
- Request size limits enforced
- Rate limiting ready (can be enabled)

### Best Practices
- Regular dependency updates
- Security scanning in CI/CD pipeline
- Principle of least privilege for database access
