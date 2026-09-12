# AI Engineering Team

AI Engineering Team installs a provider-neutral agent workflow into an existing Git repository. One CLI implements changes; distinct CLIs review medium- and high-risk work. The runner records model output, executed checks, and final status under `.ai/runs/<run-id>/`.

`primaryProvider` can be `agy`, `codex`, or `claude`. The primary cannot review its own work. `MEDIUM` requires at least one distinct reviewer and `HIGH` at least two.

## Quick start

Requires Python 3.10+, Git, the primary provider CLI, and every configured reviewer CLI.

```bash
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@<verified-commit-or-release>"
cd /path/to/project
ai-team install . --profile python
```

Do not assume the existing `v3.0.1` tag contains behavior documented for the current branch. Pin a commit or released version after checking its source.

Complete `PROJECT_CONTEXT.md` and `ai-team.config.json`, resolve installation conflicts, then commit the setup. A typical run requires an initial commit and a clean working tree.

```bash
ai-team doctor . --probe
ai-team run . "Add CSV export and tests"
```

`doctor` validates static configuration and executable presence. `--probe` invokes provider `--help`; it cannot prove authentication, model access, quota, or permission to execute a real request. Test those directly with each provider.

## Commands

```text
ai-team --version
ai-team profiles
ai-team install <project> --profile <name>
ai-team update <project> [--profile <name>]
ai-team resolve <project> <file> --strategy keep|upstream
ai-team status <project>
ai-team doctor <project> [--probe]
ai-team run <project> "<task>"
ai-team resume <run-id>|latest <project>
ai-team uninstall <project> [--dry-run]
```

`update --profile` changes the installed profile. Templates excluded by a smaller profile can remain tracked until `uninstall`; inspect them explicitly.

Existing project files are preserved on collision. Incoming templates are staged under `.ai-team/conflicts/` until explicitly resolved:

```bash
ai-team resolve . AGENTS.md --strategy keep
ai-team resolve . AGENTS.md --strategy upstream
```

`keep` accepts the project copy. `upstream` installs the staged framework copy. Review the diff first. VS Code JSONC is accepted, but merging writes normalized JSON and a backup, so comments and formatting may change.

## Verification and results

Configure real checks as argument arrays with a working directory and timeout. The runner does not infer shell commands.

```json
{"verification":{"commands":[{"argv":["python","-m","pytest"],"cwd":".","timeoutSeconds":600}]}}
```

If no safe automated check exists, set a nonempty `verification.noChecksReason`. Such a run can finish only as `PASS_WITH_NOTES`. Missing reviewers, failed reviews, malformed JSON verdicts, failing checks, unresolved findings, and a failed diff check cannot fall back to success.

Decision stages return structured JSON. `.ai/runs/<run-id>/result.json` is the canonical summary; adjacent files contain prompts, answers, stdout, and stderr.

The runner enforces `agentTimeoutSeconds`, `runTimeoutSeconds`, and `maxReviewRounds`. It currently has no token or cost accounting and no automatic resume. A timeout targets the directly started process and may not terminate every descendant on every platform.

## Bootstrap and reference

Give a coding agent this instruction:

```text
Install and configure AI Engineering Team in this repository by following docs/BOOTSTRAP.md. Inspect the repository first, preserve existing files, use a profile and verification commands supported by project evidence, and report AI_TEAM_READY exactly as specified there.
```

- [Bootstrap prompts](docs/BOOTSTRAP.md)
- [Installation](docs/INSTALL.md)
- [Configuration](docs/CONFIGURATION.md)
- [Architecture](docs/ARCHITECTURE.md)

Reviews use read-only provider modes plus filesystem snapshots, but all agents operate against the same repository. Their isolation is partly prompt-enforced, not a separate machine boundary. Risk escalation uses changed filenames and configurable globs; it is heuristic and needs conservative project-specific rules for sensitive repositories.
