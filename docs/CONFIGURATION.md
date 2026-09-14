# Configuration reference

**English** · [Polski](CONFIGURATION.pl.md)

`ai-team.config.json` is validated before `doctor` and `run`. Commands are never inferred from repository contents. Unknown keys inside `antigravity` are rejected, so a key the runner does not read fails loudly instead of drifting.

```json
{
  "primaryProvider": "agy",
  "models": {"agy": "model-id", "claude": {"default": "opus", "triage": "haiku"}},
  "providerArgs": {"codex": {"reviewer": ["--reasoning-effort", "medium"]}},
  "roleProviders": {"integrator": "codex"},
  "requireCleanWorkingTree": true,
  "createBranchForEachRun": true,
  "reuseBranchForFollowUp": false,
  "branchPrefix": "ai/",
  "reviewPolicy": {
    "LOW": ["codex"],
    "MEDIUM": ["codex"],
    "HIGH": ["claude", "codex"]
  },
  "allowUnreviewedLowRisk": false,
  "skipFinalVerificationAtLow": true,
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
  },
  "passthroughEnv": [],
  "protectedIgnoredPaths": [".env", ".env.*", "*.pem", "*.key"]
}
```

## Providers and review policy

`primaryProvider` accepts `agy`, `codex`, or `claude`.

`reviewPolicy` must define exactly `LOW`, `MEDIUM`, and `HIGH`. Reviewers must be supported providers, unique within a level, and different from `primaryProvider`. `MEDIUM` needs at least one reviewer and `HIGH` at least two. `LOW` needs one as well: the model that wrote the change should not be the only judge of it. Set `allowUnreviewedLowRisk` to `true` to accept `"LOW": []`, and record why.

Because risk escalates from the real diff after implementation, **every** reviewer named at any level must be installed before the run starts. A missing one fails the run immediately rather than after the implementation stage has been paid for. A required reviewer that is missing or fails does not fall back to success. `availabilityFallback` may remain in an older configuration for compatibility, but the runner never reads it.

`roleProviders.integrator` routes the "resolve review findings" stage to a provider other than the primary — useful when one model reviews better than it writes, or vice versa. The integrator may not be the *only* reviewer at any level, otherwise its own fix would never get an independent verdict.

Provider-specific authentication, model existence, and access are not validated statically. `doctor --probe` tests only help invocation.

## Models, effort and arguments per role

Roles are `triage`, `orchestrator`, `reviewer`, `integrator` and `verifier`.

`models` maps a provider either to one identifier (applies everywhere) or to an object keyed by role plus `default`. Cheap read-only stages can therefore use a smaller model than the implementation stage.

`antigravity.triageEffort`, `antigravity.implementationEffort` and `antigravity.verificationEffort` set `--effort` for `agy`. Defaults are `low` for triage, `high` for the writing roles (`orchestrator`, `integrator`) and `medium` for the read-only verdict roles (`reviewer`, `verifier`).

`providerArgs` is the equivalent lever for `codex` and `claude`, which have no `--effort` flag: it appends raw CLI arguments per provider and role, with `default` as a fallback role. Arguments listed here override runner defaults for the same flag, so `{"claude": {"reviewer": ["--max-turns", "12"]}}` replaces the built-in `--max-turns 30` rather than duplicating it. The runner does not validate that a flag exists in the CLI you are using.

## Verification

`verification.commands` is an array of objects:

- `argv` is required: a nonempty array of nonempty strings. It is executed directly without a shell.
- `cwd` is optional and defaults to `.`. It must resolve to an existing directory inside the project.
- `timeoutSeconds` is optional, defaults to 300, and must be a positive integer.
- `allowShellWrapper` is optional. Without it, an `argv[0]` such as `bash`, `sh`, `pwsh`, `env` or `xargs` is rejected, because it re-introduces the shell semantics the direct-exec contract exists to avoid. Setting it to `true` accepts that risk explicitly. This check stops an accidental `bash -c "… | sh"`; it is not a sandbox, since `python -c` can do the same.

Use commands already supported by project files or documentation.

When no safe automated command exists, use an empty command list and a specific nonempty `verification.noChecksReason`. This permits only `PASS_WITH_NOTES`. Omitting both commands and a reason is invalid for readiness and execution.

Checks run after model verification. Nonzero exit or failed `git diff --check` produces `CHANGES_REQUIRED`; mutation of project files aborts the run as `FAILED`.

## Limits, Git and review rounds

- `agentTimeoutSeconds`: positive integer; timeout for one provider invocation. On expiry the whole process tree is killed.
- `runTimeoutSeconds`: positive integer; overall run deadline.
- `maxReviewRounds`: integer from 1 through 5. Exhausting it ends the run as `CHANGES_REQUIRED` (exit code 2), not as a crash; the work stays on the branch. Continue with `ai-team resume <run-id> --extra-rounds N`, which discards the last round's cached verdicts and runs it again.
- `requireCleanWorkingTree`: when true, blocks a run with tracked or untracked changes.
- `createBranchForEachRun`: creates a unique `branchPrefix + run-id` branch.
- `useWorktree`: when true, executes runs in an isolated git worktree (`.ai/worktrees/<run_id>`) without switching branches in the main working tree.
- `reuseBranchForFollowUp`: when true and the current branch already starts with `branchPrefix`, continue on it instead of creating another branch. Useful for iterating on one change; leave it off when each run should stay isolated.
- `skipFinalVerificationAtLow`: when true (default) and the risk is `LOW` and an independent reviewer already returned a verdict, the primary's own final verification is skipped. Configured checks and `git diff --check` still run. This keeps a trivial change at three model invocations while replacing a self-assessment with an independent one.
- `branchPrefix`: must begin with `ai/` and cannot contain `..`.

These are time and iteration limits. They do not track tokens or cost. An interrupted run is not resumed automatically, but `ai-team resume <run-id>|latest` continues it manually, skipping stages that completed — a stage that timed out mid-answer is re-run, not accepted.

## Risk paths and content

`riskPaths` maps `LOW`, `MEDIUM`, or `HIGH` to glob arrays. Matching changed paths can only raise the current risk level. Built-in patterns escalate authentication, session, token, permission, secret, migration, schema, payment, infrastructure and CI paths, including `*.tfvars`, `Containerfile`, `.gitlab-ci.yml` and `Jenkinsfile`. The built-in list is deliberately broad; a project that names unrelated files `tokenizer.py` will see them escalate.

Beyond filenames, added lines are scanned for destructive SQL, disabled TLS verification and unsafe deserialization, which escalate to `HIGH` on their own. This is narrow by design: it catches what a filename cannot express, not everything dangerous.

Guardrail files always escalate to `HIGH` regardless of configuration: `ai-team.config.json`, `AI_TEAM.md`, `PROJECT_CONTEXT.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` and everything under `.agents/agents/`, `.claude/agents/`, `.agents/skills/` and `.claude/skills/`. An agent must not be able to weaken its own review policy in an unreviewed one-file change. Changing `ai-team.config.json` while a run is in progress aborts that run.

Some profiles seed `riskPaths` when they create a fresh `ai-team.config.json` — `postgres` and `geneteka` add migration, version and `*.sql` paths, `ocr` adds pipeline paths. An existing configuration is never modified.

## Secrets in the environment

Subprocesses receive a filtered environment. Dropped: anything matching key, token, secret, password, cookie, credential, auth, private, cert, salt, signing, session, `_DSN`, `_URI`, `_URL`, or a `PAT`/`JWT`/`SK`/`API` segment, plus the fixed names `KUBECONFIG`, `AWS_PROFILE`, `AWS_CONFIG_FILE`, `DOCKER_CONFIG`, `GIT_ASKPASS`, `SSH_ASKPASS`, `NETRC`, `PGSERVICEFILE`, `PGPASSFILE`. TLS trust anchors (`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `NODE_EXTRA_CA_CERTS`, …) and `PATH` are always kept.

This also removes `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` and `GOOGLE_APPLICATION_CREDENTIALS`. If your CLIs authenticate through environment variables rather than a stored login, list them in `passthroughEnv`:

```json
{"passthroughEnv": ["ANTHROPIC_API_KEY"]}
```

Filtering the environment is not containment. Agents run with your privileges and can read `~/.aws/credentials`, `~/.ssh/`, and `.env` from disk. Run them in a VM or container if that matters.

`protectedIgnoredPaths` lists Git-ignored files that a read-only stage still must not modify. Defaults cover `.env`, `.env.*`, `*.pem` and `*.key`.

## Language

`language` is `en` (default) or `pl`. It is written by `ai-team install --lang <en|pl>` and it decides
how the runner phrases its own stage prompts: the role preamble, the triage and implementation
instructions, the review and verification wording, and the quality rubric in the verdict prompt.

The installer writes the matching language of every agent instruction and skill into the project, so
only one language is ever present on disk and no run pays for a second copy. Keep `language` in step
with what `ai-team install --lang` put there: a Polish project with `"language": "en"` would hand the
model English stage instructions on top of Polish skills, which is the mixed-language prompt the split
exists to avoid. `ai-team update --lang <en|pl>` switches both together.

## Antigravity options

The optional `antigravity` object configures `agy`: `model`, `sandbox`, `fullAuto`, `printTimeout`, and the three effort keys above. No other key is accepted. Enabling a broad automation mode changes provider permissions; keep project and provider policy aligned. Read-only stages force a restricted provider mode where supported, and the runner also detects repository file changes.

## Worktree isolation and clean deployment

- `useWorktree` (`boolean`, default: `false`): When `true`, runs the multi-agent workflow inside an isolated `.ai/worktrees/<run_id>` Git worktree. Your working tree and active branch remain completely untouched. Can also be enabled via `--worktree` flag on the CLI.
- `autoMerge` (`boolean`, default: `false`): When `true`, automatically merges changes from isolated worktree runs into the active branch and deletes the temporary branch upon run completion, without requiring interactive confirmation. Can also be enabled via `--auto-merge` / `--merge` on the CLI.

## Autonomous skill provisioning

- `autoSkills` (`boolean`, default: `true`): When `true`, enables proactive skill provisioning by AI agents. The runner inspects project stack, task prompt keywords, and files modified during implementation to automatically install required skills from the template catalog (e.g. `devops/docker-quality` when Docker files are created, or `postgres/postgres` for SQL migrations). Can be disabled via `--no-auto-skills` flag on `ai-team run` or by setting `"autoSkills": false`.

## Automated updates and repository hygiene

- `ai-team workflow [project]`: Generates `.github/workflows/ai-team-update.yml` to enable automated weekly PRs with template and skill updates.
- `ai-team gitignore [project]`: Configures runtime log and conflict ignore rules in `.gitignore`.
- `ai-team gitignore [project] --private`: Configures complete private solo developer mode in `.git/info/exclude`.
