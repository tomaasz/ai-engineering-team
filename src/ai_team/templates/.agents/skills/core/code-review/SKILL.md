---
name: code-review
description: Evidence-based review of a diff.
---
# code-review

Priority: correctness > security > data loss > regressions > compatibility > maintainability > style. Then judge the change as a change: is it minimal for the requirement, does it avoid abstraction introduced before a second caller exists, does it match the surrounding naming and structure, and does it leave dead or duplicated code behind? Every finding: Severity, Evidence (file:line), Impact, Minimal fix. Working code that is needlessly complex is still a finding.
