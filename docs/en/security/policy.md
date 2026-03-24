# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` (latest) | ✅ |
| Older branches | ❌ |

## Reporting a vulnerability

**Please do not open public GitHub Issues for security vulnerabilities.**

Report security issues privately via **GitHub Security Advisories**:

[Report a vulnerability](https://github.com/matzalazar/exogram/security/advisories/new)

Include in your report:
- Description of the vulnerability and its potential impact
- Steps to reproduce (proof of concept if possible)
- Affected components (backend, frontend, infrastructure)
- Suggested fix if you have one

## Response timeline

| Stage | Target |
|-------|--------|
| Acknowledgement | ≤ 48 hours |
| Initial assessment | ≤ 5 business days |
| Fix or mitigation | ≤ 30 days for critical, ≤ 90 days for others |
| Public disclosure | Coordinated with reporter after fix is deployed |

## Scope

In scope:
- Authentication and session management (`accounts` app)
- Invitation token handling
- Data access controls (visibility, hermit mode, authorization)
- API endpoints and input validation
- Infrastructure configuration (Docker, Caddy, CI/CD)

Out of scope:
- Attacks requiring physical access to the server
- Denial of service via resource exhaustion
- Issues in third-party dependencies (report upstream; we'll track and upgrade)
- Social engineering attacks

## Disclosure policy

We follow coordinated disclosure. We ask that you give us a reasonable time to fix the issue before publishing details publicly. We will credit reporters in release notes unless they prefer to remain anonymous.
