from pathlib import Path
import re
import shutil
from typing import Dict, List, Any, Optional
from .utils import (
    sha256_file,
    save_json,
    load_json,
    template_root,
    profiles_root,
    ensure_git_repo,
    project_path,
)

SUFFIX = '.pl.md'
STATE_DIR = '.ai-team'
STATE_FILE = 'state.json'


def _parse_skill_meta(path: Path) -> Dict[str, str]:
    """Extract metadata (name, description) from SKILL frontmatter without external yaml parser."""
    meta = {'name': path.parent.name, 'description': ''}
    if not path.exists():
        return meta
    try:
        content = path.read_text(encoding='utf-8', errors='ignore')
        m = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if m:
            front = m.group(1)
            name_m = re.search(r'^name:\s*(.+)$', front, re.M)
            if name_m:
                meta['name'] = name_m.group(1).strip().strip('"\'')
            desc_m = re.search(r'^description:\s*(.+)$', front, re.M)
            if desc_m:
                meta['description'] = desc_m.group(1).strip().strip('"\'')
    except Exception:
        pass
    return meta


def detect_stack(project: Path) -> Dict[str, Any]:
    """Scan project files and markers to detect language, frameworks, tools, and databases."""
    project = project.resolve()
    stack = {
        'languages': [],
        'frameworks': [],
        'databases': [],
        'tools': [],
        'markers': [],
        'recommended_profile': 'core'
    }

    def has_marker(pattern: str) -> Optional[str]:
        # Fast direct check or glob
        if '*' in pattern or '?' in pattern:
            matches = list(project.glob(pattern))
            if matches:
                return matches[0].name
        else:
            p = project / pattern
            if p.exists():
                return pattern
        return None

    # 1. Python detection
    py_markers = ['pyproject.toml', 'setup.py', 'setup.cfg', 'requirements.txt', 'Pipfile', 'environment.yml']
    found_py_marker = None
    for m in py_markers:
        hit = has_marker(m)
        if hit:
            found_py_marker = hit
            stack['markers'].append(hit)
            break
    if not found_py_marker:
        # Check for any .py file in root or src/
        if list(project.glob('*.py')) or list((project / 'src').glob('**/*.py')) or list((project / 'tests').glob('**/*.py')):
            found_py_marker = '*.py'
            stack['markers'].append('*.py')
    if found_py_marker:
        stack['languages'].append('python')

    # 2. Node / TypeScript / Web detection
    js_markers = ['package.json', 'tsconfig.json', 'pnpm-lock.yaml', 'yarn.lock', 'bun.lockb']
    for m in js_markers:
        hit = has_marker(m)
        if hit:
            stack['markers'].append(hit)
            if 'typescript' not in stack['languages'] and (hit == 'tsconfig.json' or list(project.glob('**/*.ts'))):
                stack['languages'].append('typescript')
            elif 'javascript' not in stack['languages']:
                stack['languages'].append('javascript')
            break

    # 3. PostgreSQL / Database detection
    db_markers = ['alembic.ini', 'schema.prisma', 'drizzle.config.ts', 'drizzle.config.js']
    for m in db_markers:
        hit = has_marker(m)
        if hit:
            stack['markers'].append(hit)
            stack['databases'].append('postgres')
            break
    if 'postgres' not in stack['databases']:
        if (project / 'migrations').is_dir() or (project / 'alembic').is_dir() or list(project.glob('*.sql')) or list(project.glob('**/*.sql')):
            stack['markers'].append('migrations/*.sql')
            stack['databases'].append('postgres')

    # 4. Browser / E2E automation detection
    browser_markers = ['playwright.config.ts', 'playwright.config.js', 'cypress.config.ts', 'cypress.config.js']
    for m in browser_markers:
        hit = has_marker(m)
        if hit:
            stack['markers'].append(hit)
            stack['tools'].append('browser')
            break

    # 5. DevOps / Docker detection
    docker_markers = ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml', 'compose.yaml', 'compose.yml', 'Containerfile']
    for m in docker_markers:
        hit = has_marker(m)
        if hit:
            stack['markers'].append(hit)
            stack['tools'].append('docker')
            break

    # 6. OCR / Computer vision detection
    if (project / 'ocr').is_dir():
        stack['markers'].append('ocr/')
        stack['tools'].append('ocr')

    # 7. Genealogy domain detection
    if (project / 'genealogy').is_dir() or has_marker('*geneteka*') or has_marker('*.ged'):
        stack['markers'].append('genealogy/')
        stack['tools'].append('genealogy')

    # Determine recommended profile
    if 'genealogy' in stack['tools']:
        stack['recommended_profile'] = 'geneteka'
    elif 'postgres' in stack['databases'] and 'ocr' in stack['tools']:
        stack['recommended_profile'] = 'geneteka'
    elif 'postgres' in stack['databases']:
        stack['recommended_profile'] = 'postgres'
    elif 'browser' in stack['tools']:
        stack['recommended_profile'] = 'web'
    elif 'ocr' in stack['tools']:
        stack['recommended_profile'] = 'ocr'
    elif 'python' in stack['languages']:
        stack['recommended_profile'] = 'python'
    else:
        stack['recommended_profile'] = 'core'

    return stack


def suggest_skills(project: Path, lang: str = 'en') -> List[Dict[str, Any]]:
    """Suggest appropriate skills based on detected repository stack."""
    stack = detect_stack(project)
    installed_ids = {s['id'] for s in list_skills(project)['installed']}
    suggestions = []

    is_pl = lang == 'pl'

    # Core skills are always suggested if missing
    core_items = [
        ('core/code-review', 'code-review',
         'Rygorystyczny, oparty na dowodach przegląd kodu (diff).' if is_pl else 'Evidence-based, rigorous review of diffs and safety.'),
        ('core/task-planning', 'task-planning',
         'Strukturyzacja i rozbijanie zadań inżynieryjnych na etapy.' if is_pl else 'Structuring and breaking down engineering tasks.'),
        ('core/testing', 'testing',
         'Wytyczne projektowania asercji, zachowań i odpornych testów.' if is_pl else 'Behavioral testing, regression coverage, and assertions.')
    ]
    for skill_id, name, reason in core_items:
        suggestions.append({
            'id': skill_id,
            'name': name,
            'category': 'core',
            'installed': skill_id in installed_ids,
            'reason': reason
        })

    # Python
    if 'python' in stack['languages']:
        suggestions.append({
            'id': 'python/python-quality',
            'name': 'python-quality',
            'category': 'python',
            'installed': 'python/python-quality' in installed_ids,
            'reason': 'Wykryto środowisko Python w repozytorium.' if is_pl else 'Detected Python codebase and tooling.'
        })

    # PostgreSQL / DB
    if 'postgres' in stack['databases']:
        suggestions.append({
            'id': 'postgres/postgres',
            'name': 'postgres',
            'category': 'postgres',
            'installed': 'postgres/postgres' in installed_ids,
            'reason': 'Wykryto schematy migracji lub zapytania SQL.' if is_pl else 'Detected database migrations or SQL queries.'
        })

    # Browser automation
    if 'browser' in stack['tools'] or 'web' in stack['recommended_profile']:
        suggestions.append({
            'id': 'browser/browser-automation',
            'name': 'browser-automation',
            'category': 'browser',
            'installed': 'browser/browser-automation' in installed_ids,
            'reason': 'Wykryto narzędzia automatyzacji przeglądarki / E2E.' if is_pl else 'Detected browser automation / E2E testing tooling.'
        })

    # Docker / DevOps
    if 'docker' in stack['tools']:
        suggestions.append({
            'id': 'devops/docker-quality',
            'name': 'docker-quality',
            'category': 'devops',
            'installed': 'devops/docker-quality' in installed_ids,
            'reason': 'Wykryto pliki kontenerów Docker / Compose.' if is_pl else 'Detected Docker container definitions and compose specs.'
        })

    # Security
    # Audit & Security
    suggestions.append({
        'id': 'audit/full-app-audit',
        'name': 'full-app-audit',
        'category': 'audit',
        'installed': 'audit/full-app-audit' in installed_ids,
        'reason': 'Kompleksowy audyt 360° architektury, bezpieczeństwa OWASP, testów i wydajności.' if is_pl else 'Comprehensive 360° application audit covering architecture, OWASP, tests, and performance.'
    })
    suggestions.append({
        'id': 'security/secure-coding',
        'name': 'secure-coding',
        'category': 'security',
        'installed': 'security/secure-coding' in installed_ids,
        'reason': 'Standardy ochrony danych, OWASP i bezpiecznego kodowania.' if is_pl else 'OWASP defense, input validation, and secure coding standards.'
    })

    # OCR
    if 'ocr' in stack['tools']:
        suggestions.append({
            'id': 'ocr/ocr-pipeline',
            'name': 'ocr-pipeline',
            'category': 'ocr',
            'installed': 'ocr/ocr-pipeline' in installed_ids,
            'reason': 'Wykryto przetwarzanie obrazów i dokumentów OCR.' if is_pl else 'Detected OCR and image processing pipeline.'
        })

    # Genealogy
    if 'genealogy' in stack['tools']:
        suggestions.append({
            'id': 'genealogy/genealogy-etl',
            'name': 'genealogy-etl',
            'category': 'genealogy',
            'installed': 'genealogy/genealogy-etl' in installed_ids,
            'reason': 'Wykryto struktury genealogiczne i ETL.' if is_pl else 'Detected genealogy parsing and ETL structures.'
        })

    return suggestions


def list_skills(project: Path) -> Dict[str, List[Dict[str, Any]]]:
    """List both installed skills in the project and available template skills."""
    project = project.resolve()
    state_file = project / STATE_DIR / STATE_FILE
    state = load_json(state_file) if state_file.exists() else {}
    managed_paths = set(state.get('managed', {}).keys())

    installed = []
    # Check .agents/skills and .claude/skills
    seen_ids = set()
    for skill_md in sorted(project.glob('.agents/skills/*/*/SKILL*.md')):
        # Group by category/name
        cat = skill_md.parent.parent.name
        name = skill_md.parent.name
        skill_id = f'{cat}/{name}'
        if skill_id in seen_ids:
            continue
        seen_ids.add(skill_id)

        meta = _parse_skill_meta(skill_md)
        rel_posix = skill_md.relative_to(project).as_posix()
        status = 'MANAGED' if rel_posix in managed_paths else ('LOCAL' if cat == 'project' else 'CUSTOM')

        installed.append({
            'id': skill_id,
            'category': cat,
            'name': name,
            'status': status,
            'description': meta.get('description', ''),
            'path': rel_posix
        })

    # Check available templates
    tpl_root = template_root()
    available = []
    seen_tpl = set()
    for skill_md in sorted(tpl_root.glob('.agents/skills/*/*/SKILL.md')):
        cat = skill_md.parent.parent.name
        name = skill_md.parent.name
        skill_id = f'{cat}/{name}'
        if skill_id in seen_tpl or cat == 'project':
            continue
        seen_tpl.add(skill_id)
        meta = _parse_skill_meta(skill_md)
        available.append({
            'id': skill_id,
            'category': cat,
            'name': name,
            'installed': skill_id in seen_ids,
            'description': meta.get('description', '')
        })

    return {
        'installed': installed,
        'available': available
    }


def add_skill(project: Path, skill_identifier: str, lang: str = 'en') -> Dict[str, Any]:
    """Add a skill from template library to project, updating .agents and .claude alongside state.json."""
    project = ensure_git_repo(project.resolve())
    tpl_root = template_root()

    # Match identifier: can be 'cat/name' or just 'name'
    target_skill_md = None
    target_cat = None
    target_name = None

    for p in tpl_root.glob('.agents/skills/*/*/SKILL.md'):
        cat = p.parent.parent.name
        name = p.parent.name
        if skill_identifier == f'{cat}/{name}' or skill_identifier == name:
            target_skill_md = p
            target_cat = cat
            target_name = name
            break

    if not target_skill_md:
        avail = [f'{p.parent.parent.name}/{p.parent.name}' for p in sorted(tpl_root.glob('.agents/skills/*/*/SKILL.md'))]
        raise RuntimeError(f"Skill '{skill_identifier}' not found in catalog. Available: {', '.join(avail)}")

    skill_id = f'{target_cat}/{target_name}'
    suffix = SUFFIX if lang == 'pl' else '.md'

    # Source files in .agents and .claude
    src_agents = target_skill_md.parent / f'SKILL{suffix}'
    if not src_agents.exists():
        src_agents = target_skill_md

    src_claude = tpl_root / '.claude/skills' / target_cat / target_name / f'SKILL{suffix}'
    if not src_claude.exists():
        src_claude = tpl_root / '.claude/skills' / target_cat / target_name / 'SKILL.md'

    # Destinations
    dest_agents = project / '.agents/skills' / target_cat / target_name / 'SKILL.md'
    dest_claude = project / '.claude/skills' / target_cat / target_name / 'SKILL.md'

    dest_agents.parent.mkdir(parents=True, exist_ok=True)
    dest_claude.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(src_agents, dest_agents)
    created = [dest_agents.relative_to(project).as_posix()]

    if src_claude.exists():
        shutil.copy2(src_claude, dest_claude)
        created.append(dest_claude.relative_to(project).as_posix())

    # Update state.json
    state_file = project / STATE_DIR / STATE_FILE
    if state_file.exists():
        state = load_json(state_file)
        managed = state.setdefault('managed', {})
        for rel in created:
            full_path = project / rel
            managed[rel] = sha256_file(full_path)
        save_json(state_file, state)

    return {
        'id': skill_id,
        'category': target_cat,
        'name': target_name,
        'files': created
    }


def remove_skill(project: Path, skill_identifier: str, force: bool = False) -> Dict[str, Any]:
    """Remove an installed skill from the project and unregister from state.json."""
    project = ensure_git_repo(project.resolve())
    state_file = project / STATE_DIR / STATE_FILE
    state = load_json(state_file) if state_file.exists() else {}
    managed = state.get('managed', {})

    removed_files = []
    # Identify directories
    for base in ['.agents/skills', '.claude/skills']:
        base_dir = project / base
        if not base_dir.exists():
            continue
        for skill_dir in base_dir.glob('*/*'):
            cat = skill_dir.parent.name
            name = skill_dir.name
            if skill_identifier in (f'{cat}/{name}', name):
                if cat == 'project' and not force:
                    raise RuntimeError(f"Cannot remove project-local skill '{cat}/{name}' without force=True.")
                for item in skill_dir.glob('*'):
                    rel = item.relative_to(project).as_posix()
                    item.unlink()
                    removed_files.append(rel)
                    managed.pop(rel, None)
                try:
                    skill_dir.rmdir()
                    # Remove category dir if empty
                    skill_dir.parent.rmdir()
                except OSError:
                    pass

    if not removed_files:
        raise RuntimeError(f"Skill '{skill_identifier}' is not installed in the project.")

    if state_file.exists():
        state['managed'] = managed
        save_json(state_file, state)

    return {
        'id': skill_identifier,
        'removed': removed_files
    }


def filter_skills_for_task(project: Path, prompt: str = '', touched_files: Optional[List[str]] = None) -> List[Path]:
    """Select the most relevant skills for a given task prompt and modified files."""
    all_skills = sorted(project.glob('.agents/skills/*/*/SKILL.md'))
    if not all_skills:
        return []

    prompt_lower = (prompt or '').lower()
    touched_set = {f.lower() for f in (touched_files or [])}

    selected = []
    optional = []

    for skill_path in all_skills:
        cat = skill_path.parent.parent.name
        name = skill_path.parent.name

        # Core skills and project-specific skills are ALWAYS included
        if cat in ('core', 'project'):
            selected.append(skill_path)
            continue

        is_relevant = False

        if cat == 'python':
            if any(f.endswith('.py') or 'pyproject' in f or 'requirements' in f for f in touched_set) or \
               any(k in prompt_lower for k in ('python', 'pytest', 'pip', 'def ', 'class ', 'import ')):
                is_relevant = True

        elif cat == 'postgres':
            if any(f.endswith('.sql') or 'migration' in f or 'alembic' in f or 'schema' in f for f in touched_set) or \
               any(k in prompt_lower for k in ('postgres', 'sql', 'query', 'baza', 'tabel', 'migracj', 'select', 'join')):
                is_relevant = True

        elif cat == 'browser':
            if any('playwright' in f or 'cypress' in f or 'e2e' in f for f in touched_set) or \
               any(k in prompt_lower for k in ('browser', 'playwright', 'e2e', 'selenium', 'ui', 'dom', 'klik')):
                is_relevant = True

        elif cat == 'devops':
            if any('docker' in f or 'compose' in f or 'container' in f for f in touched_set) or \
               any(k in prompt_lower for k in ('docker', 'container', 'kontener', 'compose', 'image', 'build')):
                is_relevant = True

        elif cat == 'security':
            if any('auth' in f or 'token' in f or 'secret' in f or 'crypt' in f or 'cert' in f for f in touched_set) or \
               any(k in prompt_lower for k in ('secur', 'owasp', 'bezpiecz', 'auth', 'token', 'xss', 'inject', 'hasł', 'secret')):
                is_relevant = True

        elif cat == 'ocr':
            if any('ocr' in f or 'tesseract' in f for f in touched_set) or \
               any(k in prompt_lower for k in ('ocr', 'scan', 'tesseract', 'rozpoznaw', 'skan')):
                is_relevant = True

        elif cat == 'genealogy':
            if any('gedcom' in f or 'genealog' in f or 'geneteka' in f for f in touched_set) or \
               any(k in prompt_lower for k in ('genealog', 'gedcom', 'metryk', 'akt', 'geneteka')):
                is_relevant = True

        if is_relevant:
            selected.append(skill_path)
        else:
            optional.append(skill_path)

    # If context has plenty of room, include remaining optional skills as well,
    # ensuring relevant skills are ordered first.
    total_len = sum(len(p.read_text(encoding='utf-8', errors='ignore')) for p in selected + optional)
    if total_len <= 18000:
        return selected + optional
    return selected


def proactive_skill_provision(
    project: Path,
    prompt: str = '',
    touched_files: Optional[List[str]] = None,
    lang: str = 'en'
) -> List[Dict[str, Any]]:
    """Proactively discover and provision missing skills from template catalog based on stack, task, and touched files."""
    try:
        project = ensure_git_repo(project.resolve())
    except RuntimeError:
        return []

    available = {x['id']: x for x in list_skills(project)['available']}
    installed_ids = {s['id'] for s in list_skills(project)['installed']}

    prompt_lower = (prompt or '').lower()
    touched_set = {f.lower() for f in (touched_files or [])}
    stack = detect_stack(project)

    needed_skill_ids = set()

    # 1. Stack-based needs
    if 'python' in stack['languages'] and 'python/python-quality' not in installed_ids:
        needed_skill_ids.add('python/python-quality')
    if 'postgres' in stack['databases'] and 'postgres/postgres' not in installed_ids:
        needed_skill_ids.add('postgres/postgres')
    if 'browser' in stack['tools'] and 'browser/browser-automation' not in installed_ids:
        needed_skill_ids.add('browser/browser-automation')
    if 'docker' in stack['tools'] and 'devops/docker-quality' not in installed_ids:
        needed_skill_ids.add('devops/docker-quality')
    if 'ocr' in stack['tools'] and 'ocr/ocr-pipeline' not in installed_ids:
        needed_skill_ids.add('ocr/ocr-pipeline')
    if 'genealogy' in stack['tools'] and 'genealogy/genealogy-etl' not in installed_ids:
        needed_skill_ids.add('genealogy/genealogy-etl')

    # 2. Prompt-based needs
    if any(k in prompt_lower for k in ('docker', 'container', 'kontener', 'compose', 'image', 'dockerfile')):
        if 'devops/docker-quality' not in installed_ids:
            needed_skill_ids.add('devops/docker-quality')

    if any(k in prompt_lower for k in ('postgres', 'sql', 'query', 'baza', 'tabel', 'migracj', 'database', 'schema')):
        if 'postgres/postgres' not in installed_ids:
            needed_skill_ids.add('postgres/postgres')

    if any(k in prompt_lower for k in ('browser', 'playwright', 'cypress', 'e2e', 'selenium', 'przeglądark', 'dom')):
        if 'browser/browser-automation' not in installed_ids:
            needed_skill_ids.add('browser/browser-automation')

    if any(k in prompt_lower for k in ('python', 'pytest', 'pip', 'def ', 'class ', 'requirements')):
        if 'python/python-quality' not in installed_ids:
            needed_skill_ids.add('python/python-quality')

    if any(k in prompt_lower for k in ('secur', 'owasp', 'bezpiecz', 'auth', 'token', 'xss', 'inject', 'hasł', 'secret', 'szyfr', 'crypt')):
        if 'security/secure-coding' not in installed_ids:
            needed_skill_ids.add('security/secure-coding')

    if any(k in prompt_lower for k in ('ocr', 'scan', 'tesseract', 'rozpoznaw', 'skan')):
        if 'ocr/ocr-pipeline' not in installed_ids:
            needed_skill_ids.add('ocr/ocr-pipeline')

    if any(k in prompt_lower for k in ('genealog', 'gedcom', 'metryk', 'akt', 'geneteka')):
        if 'genealogy/genealogy-etl' not in installed_ids:
            needed_skill_ids.add('genealogy/genealogy-etl')

    # 3. Touched files needs (e.g. from diff after implementation)
    if any(f.endswith('.py') or 'pyproject' in f or 'requirements' in f for f in touched_set):
        if 'python/python-quality' not in installed_ids:
            needed_skill_ids.add('python/python-quality')

    if any(f.endswith('.sql') or 'migration' in f or 'alembic' in f or 'schema' in f for f in touched_set):
        if 'postgres/postgres' not in installed_ids:
            needed_skill_ids.add('postgres/postgres')

    if any('docker' in f or 'compose' in f or 'containerfile' in f for f in touched_set):
        if 'devops/docker-quality' not in installed_ids:
            needed_skill_ids.add('devops/docker-quality')

    if any('playwright' in f or 'cypress' in f or 'e2e' in f for f in touched_set):
        if 'browser/browser-automation' not in installed_ids:
            needed_skill_ids.add('browser/browser-automation')

    provisioned = []
    for skill_id in sorted(needed_skill_ids):
        if skill_id in available:
            try:
                res = add_skill(project, skill_id, lang=lang)
                provisioned.append(res)
                installed_ids.add(skill_id)
                tag = '[AUTO-SKILL]'
                msg = f"Agent proaktywnie dołączył skill '{skill_id}' do projektu." if lang == 'pl' else \
                      f"Agent proactively provisioned skill '{skill_id}' for this run."
                print(f"{tag} {msg}")
            except Exception:
                pass

    return provisioned
