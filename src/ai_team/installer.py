from pathlib import Path
import re
import shutil
from . import __version__
from .utils import (
    sha256_file,
    save_json,
    load_json,
    load_jsonc,
    template_root,
    profiles_root,
    ensure_git_repo,
    project_path,
)

VERSION = __version__
STATE_DIR = '.ai-team'
STATE_FILE = 'state.json'
LOCAL_FILES = {'PROJECT_CONTEXT.md', 'ai-team.config.json'}
LOCAL_PREFIXES = {'.agents/skills/project/', '.claude/skills/project/'}
LANGUAGES = ('en', 'pl')
SUFFIX = '.pl.md'


def _is_local(rel):
    return rel in LOCAL_FILES or any(rel.startswith(p) for p in LOCAL_PREFIXES)


def _check_language(lang):
    if lang not in LANGUAGES:
        raise RuntimeError(f"Unknown language '{lang}'. Available: {', '.join(LANGUAGES)}")
    return lang


def _has_jsonc_comments(path: Path):
    """Merging normalizes JSON; say so instead of silently dropping the user's notes."""
    if not path.exists():
        return False
    text = path.read_text(encoding='utf-8-sig')
    pattern = r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/'
    return any(m[0].startswith(('//', '/*')) for m in re.finditer(pattern, text))


def _apply_config_defaults(project, profile, lang='en'):
    """Domain profiles seed sensitive paths; a fresh config is the only safe moment."""
    defaults = profile.get('configDefaults')
    dest = project_path(project, 'ai-team.config.json')
    if not dest.exists():
        return
    config = load_json(dest)
    changed = False
    if config.get('language') != lang:
        config['language'] = lang
        changed = True
    defaults = defaults or {}
    for risk, globs in defaults.get('riskPaths', {}).items():
        current = config.setdefault('riskPaths', {}).setdefault(risk, [])
        for glob in globs:
            if glob not in current:
                current.append(glob)
                changed = True
    if changed:
        save_json(dest, config)
        print(f'[SEED] ai-team.config.json (language: {lang})')


def _profile(name):
    if name not in {x.stem for x in profiles_root().glob('*.json')}:
        raise RuntimeError(f"Nieznany profil '{name}'. Dostępne: {', '.join(sorted(x.stem for x in profiles_root().glob('*.json')))}")
    p = profiles_root() / f'{name}.json'
    if not p.exists():
        avail = ', '.join(sorted(x.stem for x in profiles_root().glob('*.json')))
        raise RuntimeError(f"Nieznany profil '{name}'. Dostępne: {avail}")
    return load_json(p)


def _all_files():
    base = template_root()
    return {p.relative_to(base).as_posix(): p for p in base.rglob('*') if p.is_file()}


def _selected(profile, lang='en'):
    """Map canonical project paths to sources; a project installs one language, never both."""
    _check_language(lang)
    inc = profile.get('include', [])
    exc = profile.get('exclude', [])
    english = {}
    polish = {}
    for rel, src in _all_files().items():
        if rel.endswith(SUFFIX):
            polish[rel[:-len(SUFFIX)] + '.md'] = src
        else:
            english[rel] = src
    out = {}
    for rel, src in english.items():
        if inc and not any(rel == x or rel.startswith(x.rstrip('/') + '/') for x in inc):
            continue
        if any(rel == x or rel.startswith(x.rstrip('/') + '/') for x in exc):
            continue
        out[rel] = polish.get(rel, src) if lang == 'pl' else src
    return out


def _state(project):
    p = project_path(project, STATE_DIR + '/' + STATE_FILE)
    return load_json(p) if p.exists() else None


def _save(project, profile, managed, conflicts=(), kept=(), lang='en'):
    save_json(project_path(project, STATE_DIR + '/' + STATE_FILE), {
        'frameworkVersion': VERSION,
        'profile': profile,
        'language': lang,
        'managed': managed,
        'conflicts': list(conflicts),
        'kept': list(kept),
    })


def _merge_tasks(project, template):
    dest = project_path(project, '.vscode/tasks.json')
    new = load_json(template)
    ownership = project_path(project, STATE_DIR + '/vscode-state.json')
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template, dest)
        save_json(ownership, new)
        return 'created'
    had_comments = _has_jsonc_comments(dest)
    try:
        old = load_jsonc(dest)
        if not isinstance(old, dict):
            raise ValueError('Expected object')
        for key in ('tasks', 'inputs'):
            if not isinstance(old.get(key, []), list) or any(not isinstance(x, dict) for x in old.get(key, [])):
                raise ValueError('Expected array of objects')
    except Exception:
        conflict = project_path(project, STATE_DIR + '/conflicts/.vscode/tasks.ai-team.json')
        conflict.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template, conflict)
        return f'conflict:{conflict}'
    baseline = load_json(ownership) if ownership.exists() else {}
    managed = {}
    conflict_found = False
    for key, identifier in [('tasks', 'label'), ('inputs', 'id')]:
        existing = old.setdefault(key, [])
        previous = {x[identifier]: x for x in baseline.get(key, []) if identifier in x}
        managed[key] = list(previous.values())
        for item in new.get(key, []):
            matches = [i for i, x in enumerate(existing) if x.get(identifier) == item[identifier]]
            if not matches:
                existing.append(item)
            elif len(matches) == 1 and existing[matches[0]] == previous.get(item[identifier]):
                existing[matches[0]] = item
            elif len(matches) == 1 and existing[matches[0]] == item:
                # Identical user-owned entries stay user-owned.
                continue
            else:
                conflict_found = True
                continue
            managed[key] = [x for x in managed[key] if x[identifier] != item[identifier]] + [item]
    if conflict_found:
        conflict = project_path(project, STATE_DIR + '/conflicts/.vscode/tasks.ai-team.json')
        conflict.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template, conflict)
    backup = project_path(project, STATE_DIR + '/backups/tasks.json.original')
    if not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, backup)
    save_json(dest, old)
    save_json(ownership, managed)
    if conflict_found:
        return f'conflict:{conflict}'
    return 'merged (comments removed; original: ' + str(backup.relative_to(project)) + ')' if had_comments else 'merged'


def _ensure_gitignores(project: Path):
    (project / '.ai/runs').mkdir(parents=True, exist_ok=True)
    ign = project / '.ai/.gitignore'
    if not ign.exists():
        ign.write_text('runs/\nlatest.txt\n', encoding='utf-8')
    (project / STATE_DIR).mkdir(parents=True, exist_ok=True)
    ign_team = project / STATE_DIR / '.gitignore'
    if not ign_team.exists():
        ign_team.write_text('conflicts/\nbackups/\n', encoding='utf-8')


def install(project: Path, profile_name: str, lang: str = 'en'):
    project = ensure_git_repo(project.resolve())
    _check_language(lang)
    if profile_name == 'auto':
        from .skills import detect_stack
        detected = detect_stack(project)
        profile_name = detected['recommended_profile']
        tag = '[AUTO-DETEKCJA]' if lang == 'pl' else '[AUTO-DETECT]'
        markers_str = ', '.join(detected['markers']) or ('ogólny' if lang == 'pl' else 'generic')
        print(f"{tag} {'Wykryte sygnatury' if lang == 'pl' else 'Detected stack'}: {markers_str}")
        print(f"{tag} {'Wybrany profil' if lang == 'pl' else 'Selected profile'}: '{profile_name}'")
    profile = _profile(profile_name)
    files = _selected(profile, lang)
    managed = {}
    conflicts = []
    seeded = []
    if _state(project):
        update(project, profile_name, lang)
        return _state(project)['managed']
    for rel in files:
        project_path(project, rel)
        project_path(project, STATE_DIR + '/conflicts/' + rel)
    project_path(project, '.ai/runs')
    project_path(project, '.ai/.gitignore')
    for rel, src in sorted(files.items()):
        if rel == '.vscode/tasks.json':
            st = _merge_tasks(project, src)
            dest = project_path(project, rel)
            if dest.exists():
                managed[rel] = sha256_file(dest)
            if st.startswith('conflict:'):
                conflicts.append(rel)
            print(f'[VSCode] {st}')
            continue
        dest = project_path(project, rel)
        if _is_local(rel) and dest.exists():
            print(f'[KEEP] {rel}')
            continue
        if dest.exists():
            conflict = project_path(project, STATE_DIR + '/conflicts/' + rel)
            conflict.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, conflict)
            managed[rel] = None
            conflicts.append(rel)
            print(f'[KEEP/CONFLICT] {rel}')
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        if _is_local(rel):
            seeded.append(rel)
            print(f'[INIT] {rel}')
        else:
            managed[rel] = sha256_file(dest)
            print(f'[ADD]  {rel}')
    if 'ai-team.config.json' in seeded:
        _apply_config_defaults(project, profile, lang)
    _ensure_gitignores(project)
    _save(project, profile_name, managed, conflicts, lang=lang)
    return managed


def update(project: Path, profile_name=None, lang=None):
    project = project.resolve()
    try:
        project = ensure_git_repo(project)
    except RuntimeError:
        pass
    state = _state(project)
    if not state:
        raise RuntimeError('Framework nie jest zainstalowany.')
    profile_name = profile_name or state['profile']
    lang = _check_language(lang or state.get('language', 'en'))
    files = _selected(_profile(profile_name), lang)
    old = state.get('managed', {})
    new = dict(old)
    conflicts = []
    kept = state.get('kept', [])
    for rel in files:
        project_path(project, rel)
        project_path(project, STATE_DIR + '/conflicts/' + rel)
    for rel, src in sorted(files.items()):
        if rel in kept:
            continue
        if _is_local(rel):
            dest = project_path(project, rel)
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                print(f'[INIT] {rel}')
            else:
                print(f'[KEEP] {rel}')
            continue
        if rel == '.vscode/tasks.json':
            st = _merge_tasks(project, src)
            dest = project_path(project, rel)
            if dest.exists():
                new[rel] = sha256_file(dest)
            if st.startswith('conflict:'):
                conflicts.append(rel)
            print(f'[VSCode] {st}')
            continue
        dest = project_path(project, rel)
        old_hash = old.get(rel)
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            new[rel] = sha256_file(dest)
            print(f'[ADD]  {rel}')
            continue
        current = sha256_file(dest)
        if current == sha256_file(src) and old_hash is not None:
            new[rel] = current
        elif old_hash is None or current != old_hash:
            conflict = project_path(project, STATE_DIR + '/conflicts/' + rel)
            conflict.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, conflict)
            new[rel] = old_hash
            conflicts.append(rel)
            print(f'[CONFLICT] {rel} -> {conflict.relative_to(project)}')
        else:
            shutil.copy2(src, dest)
            new[rel] = sha256_file(dest)
            print(f'[UPD]  {rel}')
    # Retired templates remain tracked, including unresolved retired conflicts.
    conflicts.extend(x for x in state.get('conflicts', []) if x not in files and x not in kept)
    _ensure_gitignores(project)
    _save(project, profile_name, new, conflicts, kept, lang)
    return conflicts


def status(project: Path, check_upstream: bool = False):
    project = project.resolve()
    try:
        project = ensure_git_repo(project)
    except RuntimeError:
        pass
    st = _state(project)
    if not st:
        return {'installed': False}
    upstream = None
    outdated = False
    if check_upstream:
        from .utils import check_upstream_version, version_is_newer
        upstream = check_upstream_version()
        if upstream and st.get('frameworkVersion') and version_is_newer(upstream, st.get('frameworkVersion')):
            outdated = True
    return {
        'installed': True,
        'frameworkVersion': st.get('frameworkVersion'),
        'profile': st.get('profile'),
        'language': st.get('language', 'en'),
        'managedFiles': len(st.get('managed', {})),
        'conflicts': st.get('conflicts', []),
        'upstreamVersion': upstream,
        'outdated': outdated,
    }


def uninstall(project: Path, dry_run=False):
    project = project.resolve()
    try:
        project = ensure_git_repo(project)
    except RuntimeError:
        pass
    st = _state(project)
    if not st:
        raise RuntimeError('Framework nie jest zainstalowany.')
    removed = []
    skipped = []
    for rel, old_hash in st.get('managed', {}).items():
        if rel == '.vscode/tasks.json' or rel in st.get('kept', []) or rel in st.get('conflicts', []):
            skipped.append(rel)
            continue
        dest = project_path(project, rel)
        if not dest.exists():
            continue
        if sha256_file(dest) != old_hash:
            skipped.append(rel)
            continue
        removed.append(rel)
        if not dry_run:
            dest.unlink()
    if not dry_run:
        sp = project / STATE_DIR / STATE_FILE
        if sp.exists():
            sp.unlink()
    return removed, skipped


def resolve(project: Path, relative: str, strategy='keep'):
    project = ensure_git_repo(project.resolve())
    state = _state(project)
    if not state:
        raise RuntimeError('No recorded conflict for this path')
    if relative == 'all':
        conflicts = list(state.get('conflicts', []))
        if not conflicts:
            print('[RESOLVE] Brak zarejestrowanych konfliktów.')
            return
        for conflict in conflicts:
            resolve(project, conflict, strategy=strategy)
        return
    if relative not in state.get('conflicts', []):
        raise RuntimeError('No recorded conflict for this path')
    if strategy not in {'keep', 'upstream'}:
        raise ValueError('strategy must be keep or upstream')
    dest = project_path(project, relative)
    conflict_rel = '.vscode/tasks.ai-team.json' if relative == '.vscode/tasks.json' else relative
    source = project_path(project, STATE_DIR + '/conflicts/' + conflict_rel)
    if strategy == 'keep':
        if not dest.exists():
            raise RuntimeError('Cannot keep a missing file')
        state.setdefault('kept', []).append(relative)
        state['managed'].pop(relative, None)
    else:
        # Explicit resolution is the only operation that replaces a customized file.
        backup = project_path(project, STATE_DIR + '/backups/' + relative)
        if dest.exists() and not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, backup)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        state['managed'][relative] = sha256_file(dest)
        if relative == '.vscode/tasks.json':
            save_json(project_path(project, STATE_DIR + '/vscode-state.json'), load_json(source))
    state['conflicts'].remove(relative)
    _save(project, state['profile'], state['managed'], state['conflicts'], state.get('kept', []), state.get('language', 'en'))
    if source.exists():
        source.unlink()


def install_workflow(project: Path) -> Path:
    project = project.resolve()
    try:
        project = ensure_git_repo(project)
    except RuntimeError:
        pass
    src = template_root() / '.github' / 'workflows' / 'ai-team-update.yml'
    dest = project_path(project, '.github/workflows/ai-team-update.yml')
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def _git_dir(project: Path) -> Path:
    from .utils import run
    try:
        p = run(['git', 'rev-parse', '--git-dir'], cwd=project, capture=True, check=False)
        if p.returncode == 0:
            res = Path(p.stdout.strip())
            return res if res.is_absolute() else (project / res).resolve()
    except Exception:
        pass
    return project / '.git'


def configure_gitignore(project: Path, private: bool = False) -> str:
    project = project.resolve()
    try:
        project = ensure_git_repo(project)
    except RuntimeError:
        pass

    if private:
        exclude_file = _git_dir(project) / 'info' / 'exclude'
        exclude_file.parent.mkdir(parents=True, exist_ok=True)
        existing = exclude_file.read_text(encoding='utf-8') if exclude_file.exists() else ''
        header = '# AI Engineering Team (Private / Uncommitted)'
        rules = [
            '.ai/',
            '.ai-team/',
            '.agents/',
            '.claude/',
            '.vscode/tasks.json',
            'AI_TEAM.md',
            'AGENTS.md',
            'CLAUDE.md',
            'GEMINI.md',
            'PROJECT_CONTEXT.md',
            'ai-team.config.json',
        ]
        needed = [r for r in rules if r not in existing]
        if not needed:
            return 'up-to-date'
        with exclude_file.open('a', encoding='utf-8', newline='\n') as f:
            if existing and not existing.endswith('\n'):
                f.write('\n')
            if header not in existing:
                f.write(f'\n{header}\n')
            for r in needed:
                f.write(f'{r}\n')
        return 'private-configured'
    else:
        ign_file = project / '.gitignore'
        existing = ign_file.read_text(encoding='utf-8') if ign_file.exists() else ''
        header = '# AI Engineering Team runtime & conflicts'
        rules = [
            '.ai/runs/',
            '.ai/latest.txt',
            '.ai-team/conflicts/',
            '.ai-team/backups/',
        ]
        needed = [r for r in rules if r not in existing]
        if not needed:
            return 'up-to-date'
        with ign_file.open('a', encoding='utf-8', newline='\n') as f:
            if existing and not existing.endswith('\n'):
                f.write('\n')
            if header not in existing:
                f.write(f'\n{header}\n')
            for r in needed:
                f.write(f'{r}\n')
        return 'configured'


def onboard(project: Path, profile_name='auto', solo=None, lang='pl', provider=None, no_commit=False):
    project = project.resolve()
    # 1. Ensure git repo
    git_dir = project / '.git'
    if not git_dir.exists():
        import subprocess
        subprocess.run(['git', 'init', '-b', 'main'], cwd=str(project), check=True, capture_output=True)
        print(f"[INIT] Repozytorium Git zainicjalizowane w {project}")
    
    # 2. Detect available CLI providers
    from shutil import which
    available_providers = [p for p in ('claude', 'agy', 'codex') if which(p)]
    
    if not provider:
        if 'claude' in available_providers:
            provider = 'claude'
        elif 'agy' in available_providers:
            provider = 'agy'
        elif 'codex' in available_providers:
            provider = 'codex'
        else:
            provider = 'agy'
            
    if solo is None:
        solo = len(available_providers) <= 1

    # 3. Install or update
    if not _state(project):
        install(project, profile_name, lang=lang)
    else:
        if profile_name != 'auto':
            update(project, profile_name, lang=lang)
        else:
            update(project, lang=lang)

    # 4. Resolve all conflicts
    state = _state(project)
    if state and state.get('conflicts'):
        resolve(project, 'all', strategy='upstream')
        print("[RESOLVE] Automatycznie rozwiązano konflikty szablonów ze strategią 'upstream'")

    # 5. Smart configure ai-team.config.json
    cfg_file = project / 'ai-team.config.json'
    if cfg_file.exists():
        cfg = load_json(cfg_file)
        cfg['allowUnreviewedLowRisk'] = True
        cfg['primaryProvider'] = provider
        if solo:
            cfg['singleProvider'] = True
            cfg['reviewPolicy'] = {k: [provider] for k in ('LOW', 'MEDIUM', 'HIGH')}
        ver = cfg.setdefault('verification', {'commands': [], 'noChecksReason': ''})
        cmds = ver.get('commands', [])
        reason = ver.get('noChecksReason', '').strip()
        if not cmds and not reason:
            if (project / 'package.json').exists():
                try:
                    pkg = load_json(project / 'package.json')
                    if 'test' in pkg.get('scripts', {}):
                        ver['commands'] = [{'argv': ['npm', 'test'], 'cwd': '.', 'timeoutSeconds': 300}]
                    else:
                        ver['noChecksReason'] = 'Projekt Node.js - brak zdefiniowanego skryptu npm test'
                except Exception:
                    ver['noChecksReason'] = 'Projekt Node.js'
            elif (project / 'pytest.ini').exists() or (project / 'pyproject.toml').exists() or (project / 'tests').is_dir():
                ver['commands'] = [{'argv': ['pytest'], 'cwd': '.', 'timeoutSeconds': 300}]
            elif (project / 'Cargo.toml').exists():
                ver['commands'] = [{'argv': ['cargo', 'test'], 'cwd': '.', 'timeoutSeconds': 300}]
            elif (project / 'go.mod').exists():
                ver['commands'] = [{'argv': ['go', 'test', './...'], 'cwd': '.', 'timeoutSeconds': 300}]
            else:
                ver['noChecksReason'] = 'Weryfikacja automatyczna w trakcie konfiguracji'
        save_json(cfg_file, cfg)

    # 6. Auto-clean PROJECT_CONTEXT.md
    ctx_file = project / 'PROJECT_CONTEXT.md'
    if ctx_file.exists():
        text = ctx_file.read_text(encoding='utf-8')
        if 'TODO' in text:
            proj_name = project.name
            proj_desc = 'Aplikacja / serwis'
            if (project / 'package.json').exists():
                try:
                    pkg = load_json(project / 'package.json')
                    proj_name = pkg.get('name', proj_name)
                    proj_desc = pkg.get('description', proj_desc)
                except Exception:
                    pass
            cleaned = text.replace('<!-- TODO: 2-3 zdania: czym jest ten system, kto go używa, gdzie działa -->',
                                   f'{proj_name} - {proj_desc}.')
            cleaned = cleaned.replace('<!-- TODO: Główne katalogi i ich role -->',
                                   '- Standardowa struktura projektu.')
            cleaned = cleaned.replace('<!-- TODO: Polecenia testowe, lintery, wymagane narzędzia -->',
                                   '- Testy i weryfikacja zdefiniowane w ai-team.config.json.')
            cleaned = cleaned.replace('<!-- TODO: Czego NIGDY nie robić w tym projekcie -->',
                                   '- Nie wprowadzać destrukcyjnych zmian w bazie danych bez migracji.')
            lines = [l for l in cleaned.splitlines() if 'TODO' not in l]
            ctx_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    # 7. Git commit
    if not no_commit:
        import subprocess
        status = subprocess.run(['git', 'status', '--porcelain'], cwd=str(project), capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(['git', 'add', '.'], cwd=str(project), check=True)
            subprocess.run(['git', 'commit', '-m', 'chore: setup ai-engineering-team (automated onboarding)'],
                           cwd=str(project), check=True)
            print("[GIT] Zatwierdzono konfigurację w repozytorium Git")

    # 8. Doctor check
    from .runner import doctor
    print("\n--- Diagnostyka środowiska (ai-team doctor) ---")
    ret = doctor(project, solo=solo)
    if ret == 0:
        print("\n================================================================================")
        print("  Sukces! Projekt jest w 100% gotowy do pracy z AI Engineering Team!")
        print("================================================================================\n")
        print("Aby zlecić agentowi pierwsze zadanie w bezpiecznym worktree, wykonaj:")
        if solo:
            print('  ai-team run . "Twój opis zadania" --worktree --solo\n')
        else:
            print('  ai-team run . "Twój opis zadania" --worktree\n')
    return ret
