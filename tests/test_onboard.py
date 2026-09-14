from pathlib import Path
import json
import pytest
from ai_team.installer import onboard, _state, install
from ai_team.utils import load_json


def test_onboard_empty_dir(tmp_path):
    ret = onboard(tmp_path, profile_name='core', solo=True, lang='pl', no_commit=True)
    assert (tmp_path / '.git').exists()
    assert (tmp_path / 'ai-team.config.json').exists()
    assert (tmp_path / 'PROJECT_CONTEXT.md').exists()
    
    cfg = load_json(tmp_path / 'ai-team.config.json')
    assert cfg['allowUnreviewedLowRisk'] is True
    assert cfg['singleProvider'] is True
    assert cfg['reviewPolicy']['LOW'] == [cfg['primaryProvider']]
    
    ctx = (tmp_path / 'PROJECT_CONTEXT.md').read_text(encoding='utf-8')
    assert 'TODO' not in ctx
    
    st = _state(tmp_path)
    assert st is not None
    assert len(st.get('conflicts', [])) == 0


def test_onboard_detects_node_test_and_resolves_conflicts(tmp_path):
    (tmp_path / 'package.json').write_text(
        json.dumps({'name': 'my-node-app', 'description': 'Super app', 'scripts': {'test': 'mocha'}}),
        encoding='utf-8'
    )
    # First install
    onboard(tmp_path, profile_name='core', solo=True, lang='pl', no_commit=True)
    cfg = load_json(tmp_path / 'ai-team.config.json')
    assert cfg['verification']['commands'][0]['argv'] == ['npm', 'test']
    
    # Introduce conflict
    (tmp_path / 'AI_TEAM.md').write_text('local modified version\n', encoding='utf-8')
    (tmp_path / 'AGENTS.md').write_text('local agents\n', encoding='utf-8')
    from ai_team.installer import update
    update(tmp_path, lang='pl')
    st = _state(tmp_path)
    assert len(st['conflicts']) >= 2
    
    # Onboard again should resolve all conflicts
    onboard(tmp_path, profile_name='core', solo=True, lang='pl', no_commit=True)
    st_after = _state(tmp_path)
    assert len(st_after['conflicts']) == 0
