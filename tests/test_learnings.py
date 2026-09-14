import pytest
from pathlib import Path
from ai_team.runner import _record_learnings, _learnings_context

def test_record_and_read_learnings(tmp_path):
    report = {
        'reviews': [
            {
                'provider': 'codex',
                'verdict': 'CHANGES_REQUIRED',
                'unresolved': ['Missing input validation on /api/login:42']
            }
        ],
        'verification': {
            'verdict': 'PASS_WITH_NOTES',
            'summary': 'Verification passed but tests ran slowly'
        }
    }

    _record_learnings(tmp_path, 'test-run-123', report)
    
    learnings_file = tmp_path / '.ai' / 'LEARNINGS.md'
    assert learnings_file.is_file()
    text = learnings_file.read_text(encoding='utf-8')
    assert 'test-run-123' in text
    assert '[codex] Missing input validation on /api/login:42' in text
    assert '[verification-notes] Verification passed but tests ran slowly' in text

    # Test reading context
    ctx = _learnings_context(tmp_path)
    assert 'TEAM MEMORY & PAST LEARNINGS' in ctx
    assert 'Missing input validation' in ctx

def test_record_learnings_empty(tmp_path):
    report = {
        'reviews': [{'provider': 'codex', 'verdict': 'PASS', 'unresolved': []}],
        'verification': {'verdict': 'PASS', 'summary': 'All good'}
    }
    _record_learnings(tmp_path, 'clean-run', report)
    assert not (tmp_path / '.ai' / 'LEARNINGS.md').exists()
    assert _learnings_context(tmp_path) == ''
