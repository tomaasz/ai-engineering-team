# AI Engineering Team — rules

## Goal
Deliver correct, testable, reviewable changes.

## Roles
- Architect — plan, dependencies, risk.
- Researcher — facts about the repository and its documentation.
- Implementer — minimal implementation.
- Test Engineer — independent attempts to break the change.
- Reviewer — read-only code review.
- Integrator — resolves findings with evidence.
- Verifier — final validation without edits.

## Risk
LOW — small, reversible change.
MEDIUM — several files, a new feature, an API, a significant refactor.
HIGH — auth, permissions, secrets, migrations or data, DB schema, deployment, critical logic, or a high cost of being wrong.
Files that govern how the team works (`ai-team.config.json`, `AI_TEAM.md`, `PROJECT_CONTEXT.md`,
`.agents/`, `.claude/`) are always HIGH. Never change them as a side effect of another task.

## Definition of Done
- the requirement is met,
- no incidental changes,
- appropriate tests pass,
- MEDIUM/HIGH passed an independent review,
- no unresolved BLOCKER/HIGH findings,
- the final verifier confirmed the state.

## Git
- every task on its own `ai/...` branch,
- no push, merge or deploy without explicit consent,
- no force-push, reset --hard or clean -fd without explicit consent.

## Review
Judge in this order: correctness > security > data loss > regressions > compatibility >
maintainability > style. Beyond correctness, judge the change as a change: is it minimal for the
requirement, does it avoid abstraction introduced before a second caller exists, do its naming and
structure match the surrounding code, does it leave dead or duplicated code behind?
Working code that is needlessly complex is still a finding.
Every finding: Severity, Evidence (file:line), Impact, Minimal fix.
In stages invoked by the runner, return JSON only:
{"verdict":"PASS","unresolved":[],"summary":"evidence"}
Verdict: PASS / PASS_WITH_NOTES / CHANGES_REQUIRED.
Unresolved BLOCKER/HIGH findings require CHANGES_REQUIRED.
Required reviews can never be skipped. The final result also depends on the verification commands
the runner executes and on git diff --check.

## Skills
- The orchestrator and agents automatically and proactively provision needed skills from the framework catalog when matching technologies or tasks are detected.
- Agents are empowered to proactively document project-specific architecture, conventions, and constraints in `.agents/skills/project/<name>/SKILL.md` (and mirror in `.claude/skills/project/`). Project skills are protected from being overwritten by framework updates.
