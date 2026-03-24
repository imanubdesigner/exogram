# Security Scanning in CI

The CI runs three security analysis tools on every push.

---

## bandit — Static analysis (SAST)

**Job:** `backend-lint`
**Command:** `bandit -r . -x ./migrations,./smoke_tests -ll -ii -c .bandit`

Analyzes Python code for common insecure patterns: use of `eval`,
subprocesses with shell=True, hardcoded credentials, use of weak cryptographic functions, etc.

**Flags used:**
- `-ll`: reports only issues of LOW severity or higher (includes all).
- `-ii`: reports only issues of MEDIUM confidence or higher (filters obvious false positives).
- `-c .bandit`: reads configuration from `backend/.bandit`.

**`.bandit` configuration:**
```ini
skips: ['B101', 'B311']
```
- `B101` (use of `assert`): expected false positive in tests. `assert` in tests is correct.
- `B311` (use of `random`): in this project `random` is not used for cryptography, only for application logic. Tokens and secrets use `secrets` from stdlib.

---

## pip-audit — Dependency vulnerabilities

**Job:** `backend-lint`
**Command:** `pip-audit -r requirements.txt`

Queries the PyPA (OSV) database to detect known CVEs in Python dependencies
declared in `requirements.txt`. Does not require authentication or an API key.

Replaces `safety` (which required authentication from version 2.3.5 onwards).

If it finds vulnerabilities with CRITICAL or HIGH severity, the job fails and blocks the merge.

**Action on an alert:** update the affected package in `requirements.txt` and `requirements.in` if it exists.

---

## flake8 + isort — Code quality

**Job:** `backend-lint` (same job as bandit and pip-audit)

Although they are not strictly security tools, code consistency
reduces the likelihood of introducing bugs through confusion:

- **flake8:** detects syntax errors, unused imports, undefined variables.
- **isort:** verifies that imports are sorted. Reduces unnecessary diffs in PRs.

**Configuration in `backend/setup.cfg`:**
- `max-line-length = 120`
- Exclusions: `migrations/`, `__pycache__/`, `.venv/`, `smoke_tests/`
- isort excludes `*/migrations/*` via `skip_glob`

---

## Why there is no container scan

The Trivy job (container scan) was removed because the binary could not be downloaded
reliably from the GitHub Actions CI environment. As an alternative:

- Python dependencies are already covered by `pip-audit`.
- The Dockerfile runs `apt-get upgrade -y` at build time, which updates system packages with available patches.
- If container scanning is desired in the future, consider running it locally with `trivy image` before pushing, or using a registry service with integrated scanning (Docker Hub, GitHub Container Registry, etc.).
