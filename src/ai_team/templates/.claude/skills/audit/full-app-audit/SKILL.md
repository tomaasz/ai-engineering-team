---
name: full-app-audit
description: Comprehensive 360-degree application audit covering architecture, OWASP security, code quality, test coverage, performance, and DevOps readiness.
---
# full-app-audit

Perform a rigorous, end-to-end 360° audit of the target application across 6 critical dimensions.

## Audit Dimensions

### 1. Architecture & Code Structure
- **Design Patterns & Boundaries**: Verify separation of concerns, domain layering, and modular cohesion.
- **Technical Debt & Antipatterns**: Identify God classes/modules, circular dependencies, spaghettified control flows, and code duplication.
- **Dead & Orphaned Code**: Spot unused exports, obsolete utilities, dead routes, and unreferenced packages.

### 2. Security & Vulnerabilities (OWASP Top 10 & CWE)
- **Secrets & Credentials**: Scan for hardcoded API keys, tokens, passwords, private keys, or exposed `.env` files.
- **Injection Vulnerabilities**: Inspect SQL/NoSQL queries for parameterization; inspect shell/command executions, template injections, and regex DoS.
- **Authentication & Authorization**: Verify token lifetimes, password hashing algorithms (bcrypt/argon2), JWT validation, IDOR/BOLA, and role checks.
- **Data Protection & Headers**: Check sanitization on input/output, CORS configuration (disallow `*` with credentials), CSP, and security headers.
- **Dependencies & Supply Chain**: Check for known CVEs, outdated packages, and lockfile integrity.

### 3. Reliability, Error Handling & Edge Cases
- **Exception Safety**: Detect swallowed errors (`catch {}`, `except: pass`), unhandled Promise rejections, and missing error propagation.
- **Concurrency & Race Conditions**: Check shared mutable state, race hazards in async operations, and atomic operations.
- **Resource Management**: Check for unclosed database connections, dangling file descriptors, unhandled process signals (SIGTERM/SIGINT), and memory leaks.

### 4. Performance & Data Access
- **Database Access Patterns**: Flag N+1 query loops, missing indexes on foreign keys/filters, and unbounded queries without pagination.
- **Event Loop & Concurrency**: Ensure CPU-heavy tasks do not block the event loop in async runtimes (Node.js/asyncio).
- **Caching & Payloads**: Verify proper caching strategies and payload compression.

### 5. Testing & Quality Assurance
- **Coverage Gaps**: Identify critical business logic and authorization paths lacking tests.
- **Test Integrity**: Detect mock-only tests that test mocks rather than system behavior; verify edge cases and failure paths.

### 6. DevOps, Containerization & Operations
- **Container Hygiene**: Multi-stage Docker builds, non-root user execution, pinned base images, minimal attack surfaces.
- **Observability**: Structured JSON logging, correlation IDs, lack of sensitive data in logs, healthcheck endpoints (`/health`, `/ready`).
- **Configuration Hygiene**: Strict runtime validation of environment variables on boot (fail-fast).

## Report Output Format

Generate the final audit report into `docs/AUDIT.md` (or specified output path) using the standard matrix and actionable remediation code snippets.

