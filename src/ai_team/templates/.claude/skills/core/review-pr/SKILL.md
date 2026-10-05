---
name: review-pr
description: Evidence-based two-phase PR review and cross-model audit in clean context.
---
# review-pr

Two-phase unbiased PR review and cross-model audit.

## Protocol
1. **Context Isolation**: Reset conversation state (`/clear` in interactive sessions, or isolated `--bare`/`--ephemeral` session). Do not review code with authoring bias ("grading own homework" antipattern).
2. **Diff Extraction**: Fetch target PR/branch diff against base ref using `gh pr diff` or `git diff base...HEAD`.
3. **Cross-Model Adversarial Audit**: Invoke an independent reviewer model (Codex, Claude, or independent-reviewer agent) to probe for:
   - Correctness, regressions, and silent breakage
   - Security, secrets, and OWASP vulnerabilities
   - Edge cases, concurrency races, and resource leaks
   - Test coverage gaps
4. **Structured Findings**: Every finding must specify: Severity (CRITICAL, HIGH, MEDIUM, LOW), Evidence (file:line), Impact, Minimal fix.
5. **Self-Healing**: Extract recurrent failure patterns and propose updates to project rules (`CLAUDE.md`, skills, linters).
