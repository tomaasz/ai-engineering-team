"""Every human-facing document ships in both languages and says so."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# Docs a reader opens directly. Templates are excluded: a project installs one language.
DOCS = ['README.md', 'CONTRIBUTING.md', 'SECURITY.md', 'CHANGELOG.md',
        'docs/ARCHITECTURE.md', 'docs/CONFIGURATION.md', 'docs/INSTALL.md']


def polish(name):
    return name.replace('.md', '.pl.md')


@pytest.mark.parametrize('name', DOCS)
def test_every_document_has_a_polish_counterpart(name):
    assert (ROOT / polish(name)).is_file(), f'missing translation: {polish(name)}'


@pytest.mark.parametrize('name', DOCS)
def test_both_versions_link_to_each_other(name):
    """A reader who lands on the wrong language must find the other one without searching."""
    english = (ROOT / name).read_text(encoding='utf-8')
    assert Path(polish(name)).name in english, f'{name} does not link to its Polish version'
    assert Path(name).name in (ROOT / polish(name)).read_text(encoding='utf-8')


@pytest.mark.parametrize('name', DOCS)
def test_translations_keep_the_same_section_structure(name):
    """A translation that drifts in structure is how documentation goes stale unnoticed."""
    def headings(path):
        return [line.split(' ', 1)[0] for line in path.read_text(encoding='utf-8').splitlines()
                if line.startswith('#')]
    assert headings(ROOT / name) == headings(ROOT / polish(name)), \
        f'{name} and its translation have different heading structures'


def test_bootstrap_stays_a_single_bilingual_file():
    """BOOTSTRAP is pasted into an agent, so both prompts belong side by side."""
    text = (ROOT / 'docs/BOOTSTRAP.md').read_text(encoding='utf-8')
    assert '## English' in text and '## Polski' in text
    assert not (ROOT / 'docs/BOOTSTRAP.pl.md').exists()
