# Configuration reference

`ai-team.config.json` is validated before `doctor` and `run`. Commands are never inferred from repository contents.

```json
{
  "primaryProvider": "agy",
  "models": {"agy": "model-id", "codex": "model-id", "claude": "model-id"},
  "requireCleanWorkingTree": true,
  "createBranchForEachRun": true,
  "branchPrefix": "ai/",
  "reviewPolicy": {
    "LOW": [],
    "MEDIUM": ["codex"],
    "HIGH": ["claude", "codex"]
  },
  "agentTimeoutSeconds": 3600,
  "runTimeoutSeconds": 14400,
  "maxReviewRounds": 2,
  "verification": {
    "commands": [
      {"argv": ["python", "-m", "pytest"], "cwd": ".", "timeoutSeconds": 600}
    ]
  },
  "riskPaths": {
    "HIGH": ["infra/**", "src/security/**"],
    "MEDIUM": ["src/api/**"]
  }
}
```

## Providers and review policy

`primaryProvider` accepts `agy`, `codex`, or `claude`. `models` optionally maps those provider names to model identifiers supported by their CLIs.

`reviewPolicy` must define exactly `LOW`, `MEDIUM`, and `HIGH`. Reviewers must be supported providers, unique within a level, and different from `primaryProvider`. `MEDIUM` needs at least one reviewer and `HIGH` at least two. A required reviewer that is missing or fails does not fall back to success. `availabilityFallback` may remain in an older configuration for compatibility, but does not relax this rule.

Provider-specific authentication, model existence, and access are not validated statically. `doctor --probe` tests only help invocation.

## Verification

`verification.commands` is an array of objects:

- `argv` is required: a nonempty array of nonempty strings. It is executed directly without a shell.
- `cwd` is optional and defaults to `.`. It must resolve to an existing directory inside the project.
- `timeoutSeconds` is optional, defaults to 300, and must be a positive integer.

Use commands already supported by project files or documentation. Do not encode pipes, redirects, `&&`, or shell scripts as a single `argv` string.

When no safe automated command exists, use an empty command list and a specific nonempty `verification.noChecksReason`. This permits only `PASS_WITH_NOTES`. Omitting both commands and a reason is invalid for readiness and execution.

Checks run after model verification. Nonzero exit or failed `git diff --check` produces `CHANGES_REQUIRED`; mutation of project files aborts the run as `FAILED`.

## Limits and Git

- `agentTimeoutSeconds`: positive integer; timeout for one provider invocation.
- `runTimeoutSeconds`: positive integer; overall run deadline.
- `maxReviewRounds`: integer from 1 through 5.
- `requireCleanWorkingTree`: when true, blocks a run with tracked or untracked changes.
- `createBranchForEachRun`: creates a unique `branchPrefix + run-id` branch.
- `branchPrefix`: must begin with `ai/` and cannot contain `..`.

These are time and iteration limits. They do not track tokens or cost. An interrupted run is not resumed automatically, but `ai-team resume <run-id>|latest` continues it manually, skipping already-completed stages. Direct subprocess timeout may leave descendant processes on some platforms.

## Risk paths

`riskPaths` maps `LOW`, `MEDIUM`, or `HIGH` to glob arrays. Matching changed paths can only raise the current risk level. Built-in patterns already escalate common authentication, secret, migration, infrastructure, workflow, payment, permission, and schema paths. Globs inspect names rather than code semantics, so add project-specific sensitive paths and treat the result as heuristic.

## Antigravity options

The optional `antigravity` object configures `agy`, including `model`, `sandbox`, `fullAuto`, and `printTimeout`. Enabling a broad automation mode changes provider permissions; keep project and provider policy aligned. Read-only stages force a restricted provider mode where supported, and the runner also detects repository file changes.
