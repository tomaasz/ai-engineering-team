# Project Context

## Project goal
TODO

## Stack
TODO

## Main commands
For each command record the working directory, its requirements, the source in the repository and
its status: confirmed in configuration / executed / unverified.
Configure the safe check commands in ai-team.config.json as well:
verification.commands = [{"argv":["program","argument"],"cwd":".","timeoutSeconds":300}].
Never register migrations or deployments as automated checks.
If the project has no automated checks, justify verification.noChecksReason.
- install: TODO
- lint: TODO
- typecheck: TODO
- unit tests: TODO
- integration tests: TODO
- build: TODO

## Critical areas
TODO

## Areas requiring explicit consent before a change
TODO

## Conventions
TODO

## Patterns to imitate
Name 2-3 existing files that best represent the target style of the project
(for example a domain module, a test, the API layer). A model copies style from examples far more
reliably than from descriptive rules. For each one, say what exactly to take from it.
- TODO: path — what to imitate
- TODO: path — what to imitate

## What not to imitate
List the files or areas considered technical debt, whose pattern must not be copied.
TODO

## Monorepo components
List the components, directories, stacks and their commands; for a single project: not applicable.

## Definition of Done
The requirement is met, the required reviews are complete, the checks exit 0,
and no BLOCKER/HIGH finding is unresolved. Missing tests must be explicitly justified.
