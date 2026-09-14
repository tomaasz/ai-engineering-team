# Architecture

**English** · [Polski](ARCHITECTURE.pl.md)

The package contains a dispatcher, provider adapters, installer, profiles, agent instructions, skills, and IDE templates. Installation copies the selected profile into the target Git repository and records checksums of managed files and unresolved conflicts in `.ai-team/state.json`.

## Run Pipeline

```text
prompt
  -> readiness check (primary provider + every reviewer CLI across any policy level)
  -> read-only triage (JSON risk level)
  -> implementation by primary provider
  -> risk escalation based on modified paths, added content, and guardrail files
  -> independent reviews (JSON verdicts) based on generated diff.patch
  -> integration when required (primary provider or roleProviders.integrator)
  -> bounded review rounds
  -> final read-only verifier (JSON verdict), skipped for LOW when a reviewer already passed
  -> configured argv verification commands + git diff --check
  -> result.json
```

The primary provider can be `agy`, `codex`, or `claude`. Review policy must specify different providers and cannot include the primary provider. `LOW` requires one reviewer unless `allowUnreviewedLowRisk` is set, `MEDIUM` requires at least one, and `HIGH` requires at least two. Missing CLIs and failing or invalid reviews abort the run; the runner does not honor `availabilityFallback` for silent bypass. Because risk can escalate based on the actual diff, every reviewer CLI referenced anywhere in policy must be installed before starting.

Triage returns `{"risk":"LOW|MEDIUM|HIGH"}`. Reviews and final verification return `verdict`, `unresolved`, and `summary`. A passing verdict cannot contain unresolved findings. The dispatcher parses JSON instead of regex matching `PASS` in freeform text. An invalid response identifies the provider, stage file, and the first 200 characters of the received output.

Review prompts include an explicit quality rubric (correctness first, then whether the change is minimal, free of premature abstraction, and consistent with surrounding code) and the contents of every `.agents/skills/*/*/SKILL.md`.

Risk is computed from the initial triage classification, count of changed files, built-in sensitive path globs, `riskPaths`, added content patterns, and a fixed list of guardrail files. Files defining how the team reviews itself — `ai-team.config.json`, `AI_TEAM.md`, `PROJECT_CONTEXT.md`, AI instruction files, and anything under `.agents/agents/`, `.claude/agents/`, `.agents/skills/`, and `.claude/skills/` — always escalate to `HIGH`. The runner also halts if `ai-team.config.json` changes during the run. Path matching remains a heuristic; content-based matching targets destructive SQL, disabled TLS verification, and unsafe deserialization.

Every run records its base ref, branch, prompt, stage outputs, stderr, check logs, and canonical `.ai/runs/<run-id>/result.json`. When running with `--worktree` (or `"useWorktree": true`), the entire execution is isolated in `.ai/worktrees/<run_id>`, leaving the active branch untouched. Upon completion, changes are cleanly committed to `ai/<run-id>`, and the CLI prompts whether to merge into the active branch with automatic temporary branch cleanup. In standard direct mode, a dedicated branch is used without automated push or deploy.

Verification commands execute directly via `argv` without a shell. An `argv[0]` restoring a shell (`bash`, `sh`, `pwsh`, `env`, `xargs`, ...) is rejected unless `allowShellWrapper` is set. A failing check command, file changes during verification, failed `git diff --check`, `CHANGES_REQUIRED`, or exhausted review rounds block success. An explicit `noChecksReason` is permitted but caps the run status at `PASS_WITH_NOTES`.

## Durability

- Stage outputs are written atomically. Commands interrupted by timeout or error leave behind `<stage>.failed` for diagnosis and do not leave `<stage>`, and a stage is only complete once `<stage>.done` exists.
- Process timeouts terminate the entire process tree (`taskkill /T /F` on Windows, `killpg` elsewhere), preventing orphaned background processes from modifying the repository.
- Exhausted review rounds finish the run as `CHANGES_REQUIRED` with exit code 2. Work remains on the branch, and `ai-team resume <run-id> --extra-rounds N` reopens the final round.

## Boundaries

- `agentTimeoutSeconds` bounds a single agent invocation; `runTimeoutSeconds` bounds the total run; `maxReviewRounds` bounds review/integration cycles.
- Token accounting and cost tracking are not included. `ai-team resume <run-id>|latest` re-enters an interrupted run after verifying branch consistency, but resume is manual, never automatic.
- Subprocess environments strip credential-like variables, connection strings, agent sockets, and fixed patterns (`KUBECONFIG`, `AWS_PROFILE`, ...). Provider API keys are also stripped unless explicitly listed in `passthroughEnv`.
- Reviewers run in provider read-only modes and filesystem snapshots include tracked, untracked, `protectedIgnoredPaths`, and the run directory itself.
- Installation conflicts persist until resolved via `resolve`. Reducing a profile may leave retired templates tracked until `uninstall`.
- VS Code JSONC merging creates backups, normalizes JSON, and reports when comments are dropped.
