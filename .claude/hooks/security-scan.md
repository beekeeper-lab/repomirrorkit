# Hook Pack: Security Scan

## Category
code-quality

## Purpose

Detects security issues at key workflow points: vulnerable dependencies, hardcoded secrets, static analysis findings, and license violations. Acts as a safety net that catches security problems before they reach production.

## Hooks

| Hook Name | Trigger | Check | Pass Criteria | Fail Action |
|-----------|---------|-------|---------------|-------------|
| `dependency-audit` | `pre-commit` | Scan dependency manifests for known vulnerabilities (e.g. `pip-audit`, `npm audit`) | No high or critical severity vulnerabilities | Block commit; list vulnerable packages with advisories |
| `secret-detection` | `pre-commit` | Scan changed files for hardcoded secrets, API keys, and credentials | Zero secrets detected | Block commit; list files and line numbers with potential secrets |
| `sast-scan` | `post-task-complete` | Run static application security testing on changed code (e.g. `bandit`, `semgrep`) | No high-severity findings | Block task completion; list findings with CWE references |
| `license-check` | `pre-release` | Verify all dependencies use approved licenses | All licenses on the approved list | Block release; list packages with unapproved licenses |

## Configuration

- **Default mode:** enforcing for hardened and regulated postures; advisory for baseline
- **Timeout:** 120 seconds per hook (dependency-audit and sast-scan may need full scan time)
- **Customization:** Projects can maintain an allowlist for known false positives in `.foundry/security-allowlist.yml`. Allowlisted items still produce advisory warnings but do not block.

## Posture Compatibility

| Posture | Included | Default Mode |
|---------|----------|--------------|
| `baseline` | Yes | advisory |
| `hardened` | Yes | enforcing |
| `regulated` | Yes | enforcing |

At baseline posture, security scans run but only warn. At hardened and regulated postures, they block on failures.
