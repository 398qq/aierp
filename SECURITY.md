# Security Policy

## Supported Versions

| Version | Supported          | Notes                                  |
| ------- | ------------------ | -------------------------------------- |
| 2.2.x (backend) / 2.1.x (frontend) | :white_check_mark: | Current release line. Receives security patches. |
| < 2.0 (both)               | :x:                | End of life. Upgrade before reporting issues. |

Backend version: `backend/app/config.py` `Settings.VERSION`. Frontend version: `frontend/package.json` `version`. The `master` branch carries the supported release.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Use one of these private channels:

1. **GitHub Security Advisories** (preferred): <https://github.com/398qq/aierp/security/advisories/new>
2. **Direct email to maintainers**: see `CODEOWNERS` for the current rotation.

Include in the report:

- Affected component (backend / frontend / infrastructure) and version
- Reproduction steps or proof-of-concept
- Impact assessment (what data / access is exposed)
- Whether the issue is already known to be exploited in the wild

### What to expect

- **Initial acknowledgement**: within 3 business days
- **Triage and severity assessment** (using CVSS v3.1): within 7 business days
- **Patch for critical / high severity**: target 30 days from confirmation
- **Public disclosure**: coordinated with reporter; default is after a fix is released

We follow [coordinated disclosure](https://en.wikipedia.org/wiki/Coordinated_vulnerability_disclosure). Please give us a reasonable window before publishing details.

## Security Architecture (summary)

Defense-in-depth layers, each described in `docs/architecture/adr/`:

| Layer | Mechanism | Where |
| --- | --- | --- |
| **Authentication** | JWT (`Authorization: Bearer` preferred, `aierp_token` httpOnly cookie fallback), 8h default expiry, `jti` Redis blacklist, `User.token_version` invalidation | `backend/app/core/security.py`, `backend/app/api/deps.py` |
| **Authorization** | RBAC: `Depends(require_perm(resource, action))` on every new endpoint; single EXISTS query, `admin` role bypass, Redis cache 10s | `backend/app/core/permissions.py` |
| **Data isolation** | Tenant/owner scoping on every query; soft delete (`TimestampMixin` + `deleted_at IS NULL` filter) | `backend/app/models/base.py` |
| **Encryption at rest** | Field-level encryption for PII columns | `backend/app/core/field_encryption.py` |
| **Encryption in transit** | HTTPS in production (Strict-Transport-Security); no HTTP fallback |
| **Rate limiting** | Per-IP and per-user, Redis-backed; auth and write endpoints hardened | `backend/app/core/rate_limit.py` |
| **Headers** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` for camera/mic/geo | `backend/app/core/security_headers.py` |
| **Audit** | `created_by` / `updated_by` populated from `request_context` by event listeners; `request_id` propagated through logs, errors, and slow-query log | `backend/app/core/request_context.py` |
| **PII policy** | Field allowlist; PII fields never logged or returned in error messages | `backend/app/core/pii_policy.py` |
| **Frontend** | Zod runtime validation at API boundaries; CSP; no `dangerouslySetInnerHTML` without sanitization; tokens in httpOnly cookies (not `localStorage`) | `frontend/src/api/schemas/`, `docs/FRONTEND_SECURITY.md` |
| **External dependencies** | Bounded slow paths (AI / OCR / PDF / logistics / payment): explicit `timeout` + tenacity retries + safe fallbacks | various |
| **Migrations** | Alembic is the source of truth; new structural changes never go only into `app/migrations/*.sql` | `CONTRIBUTING.md` §Migrations |

## Known Accepted Risks

These are tracked separately so they don't get lost:

- **react-router 7.18.2 — 2 high-severity CVEs** — tracked in [#100](https://github.com/398qq/aierp/issues/100). Not exploitable in this codebase (RSC mode is not used; we are a UmiJS Max client-side SPA). Awaiting upstream fix.

## Out-of-scope

- **Third-party AI provider availability / data handling** — see [SiliconFlow's own security policy](https://docs.siliconflow.cn/) for `bge-large-zh-v1.5` embedding and `DeepSeek-V4-Flash` model behavior.
- **Customer's deployment configuration** — TLS termination, reverse proxy headers, secret rotation cadence are the deployer's responsibility. See `docs/OPS.md`.
- **Penetration testing on `dev` / staging** — only `master` and tagged releases are in scope for vulnerability reports.

## Security tooling (CI)

| Tool | Scope | Schedule | File |
| --- | --- | --- | --- |
| `pip-audit` | Python deps | Every push + Mon 01:30 UTC | `.github/workflows/security-audit.yml` |
| `npm audit --audit-level=high --omit=dev` | JS deps (prod only) | Every push + Mon 01:30 UTC | `.github/workflows/security-audit.yml` |
| Dependabot | Auto-PR for outdated deps | Mon 09:00 Asia/Shanghai | `.github/dependabot.yml` |
| CodeQL | Python + JS/TS static analysis | Tue 02:00 UTC + every push | `.github/workflows/codeql.yml` |
| `bandit` | Python security linter | pre-commit | `.pre-commit-config.yaml` |
| `detect-secrets` | Secret scan | pre-commit | `.pre-commit-config.yaml` |

See `CONTRIBUTING.md` §Security Audit for the full triage playbook.
