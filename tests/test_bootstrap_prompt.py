"""The bootstrap prompt must produce a configuration the validator accepts."""
from pathlib import Path

import pytest

DOC = Path(__file__).resolve().parent.parent / 'docs' / 'BOOTSTRAP.md'

# Settings a bootstrapping agent cannot infer and whose absence breaks install or the first run.
BOOTSTRAP_CRITICAL = [
    'allowUnreviewedLowRisk',   # LOW without a reviewer now fails validation
    'passthroughEnv',           # provider API keys are stripped from subprocess environments
    'allowShellWrapper',        # a bash -c verification command is rejected without it
    'noChecksReason',
    'riskPaths',
]


def sections():
    text = DOC.read_text(encoding='utf-8')
    english, polish = text.split('## Polski')
    return {'English': english, 'Polski': polish}


@pytest.mark.parametrize('language', ['English', 'Polski'])
def test_both_prompts_cover_every_bootstrap_critical_setting(language):
    body = sections()[language]
    missing = [key for key in BOOTSTRAP_CRITICAL if key not in body]
    assert not missing, f'{language} bootstrap prompt omits: {missing}'


@pytest.mark.parametrize('language', ['English', 'Polski'])
def test_both_prompts_require_a_low_risk_reviewer(language):
    body = sections()[language]
    assert 'LOW' in body, 'the prompt must state the LOW review requirement, not only MEDIUM and HIGH'


@pytest.mark.parametrize('language', ['English', 'Polski'])
def test_both_prompts_require_every_policy_reviewer_to_be_installed(language):
    """Risk escalates from the real diff, so a HIGH-only reviewer must exist before the first run."""
    body = sections()[language].lower()
    assert 'escalat' in body or 'eskal' in body


@pytest.mark.parametrize('language', ['English', 'Polski'])
def test_readiness_requires_doctor_to_pass(language):
    """doctor now fails on unfilled PROJECT_CONTEXT placeholders; YES must depend on it."""
    body = sections()[language]
    assert 'doctor' in body and 'TODO' in body
