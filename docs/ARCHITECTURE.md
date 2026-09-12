# Architecture

The package contains the dispatcher, provider adapters, installer, profiles, agent instructions, skills, and IDE templates. Installation copies the selected profile into a Git project and records managed checksums and unresolved conflicts in `.ai-team/state.json`.

## Run pipeline

```text
prompt
  -> read-only triage (JSON risk)
  -> primary provider implementation
  -> risk escalation from changed paths
  -> independent reviews (JSON verdicts)
  -> primary-provider integration when required
  -> bounded review rounds
  -> read-only final verifier (JSON verdict)
  -> configured argv checks + git diff --check
  -> result.json
```

The primary provider may be `agy`, `codex`, or `claude`. Review policy must use distinct providers and cannot contain the primary. `LOW` needs zero or more reviewers, `MEDIUM` at least one, and `HIGH` at least two. Missing CLIs and failed or malformed reviews stop the run; `availabilityFallback` does not permit success.

Triage returns `{"risk":"LOW|MEDIUM|HIGH"}`. Reviews and final verification return `verdict`, `unresolved`, and `summary`. Passing verdicts cannot contain unresolved findings. The dispatcher parses JSON instead of searching prose for `PASS`.

Risk is reevaluated from the initial classification, changed-file count, built-in sensitive filename globs, and `riskPaths`. Filename matching remains a heuristic and does not understand code semantics.

Each run records its base ref, branch, prompt, stage output, stderr, check logs, and canonical `.ai/runs/<run-id>/result.json`. A generated branch is used by default. No automatic commit, push, merge, or deployment occurs.

Verification commands run directly from `argv`, without a shell. A failed command, file changes during verification, failed `git diff --check`, `CHANGES_REQUIRED`, or exhausted review rounds prevents success. An explicit `noChecksReason` is allowed, but yields `PASS_WITH_NOTES`.

## Boundaries

- `agentTimeoutSeconds` limits one directly launched agent; `runTimeoutSeconds` limits the overall deadline; `maxReviewRounds` limits review/integration cycles.
- There is no token or cost accounting. `ai-team resume <run-id>|latest` re-enters an interrupted run after verifying the branch still matches, but resume is manual, not automatic.
- Timeout targets the direct process; complete descendant-process cleanup is not guaranteed on every platform.
- Reviewers use read-only modes and filesystem snapshots, but share one repository. Independence from other reports is prompt-enforced too, so this is not container or host isolation.
- Installer conflicts remain until `resolve`. Profile reductions may leave retired templates tracked until uninstall.
- VS Code JSONC merge creates a backup, normalizes JSON, and can remove comments.
