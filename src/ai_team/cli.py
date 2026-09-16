import argparse, sys
from pathlib import Path
from .installer import install, update, status, uninstall, resolve, install_workflow, configure_gitignore, onboard
from .runner import run_team, doctor, resume_team, runs, review_run
from .skills import list_skills, suggest_skills, add_skill, remove_skill, detect_stack
from .utils import profiles_root
from .sarif import export_sarif, markdown_to_sarif
from . import __version__

def parser():
    p = argparse.ArgumentParser(prog='ai-team')
    p.add_argument('--version', action='version', version=__version__)
    s = p.add_subparsers(dest='command', required=True)
    s.add_parser('profiles')
    x = s.add_parser('install')
    x.add_argument('project', nargs='?', default='.')
    x.add_argument('--profile', default='core')
    x.add_argument('--auto', action='store_true', help='Auto-detect repository stack and select best profile')
    x.add_argument('--lang', choices=['en', 'pl'])

    x = s.add_parser('workflow', help='Install GitHub Actions automated update workflow')
    x.add_argument('project', nargs='?', default='.')

    x = s.add_parser('gitignore', help='Configure .gitignore or private .git/info/exclude rules')
    x.add_argument('project', nargs='?', default='.')
    x.add_argument('--private', action='store_true', help='Add exclusions to private .git/info/exclude instead of root .gitignore')

    x = s.add_parser('update')
    x.add_argument('project', nargs='?', default='.')
    x.add_argument('--profile')
    x.add_argument('--lang', choices=['en', 'pl'])
    x.add_argument('--check', action='store_true', help='Check whether a new version is available on GitHub')

    x = s.add_parser('status')
    x.add_argument('project', nargs='?', default='.')

    x = s.add_parser('doctor')
    x.add_argument('project', nargs='?', default='.')
    x.add_argument('--probe', action='store_true')
    x.add_argument('--solo', '--single-provider', dest='solo', action='store_true', default=None,
                   help='Verify readiness for solo mode with primaryProvider only')

    x = s.add_parser('resolve')
    x.add_argument('project')
    x.add_argument('file', help='Conflict file path (or "all" to resolve all conflicts)')
    x.add_argument('--strategy', choices=['keep', 'upstream'], required=True)

    for cmd_name in ('skill', 'skills'):
        sk = s.add_parser(cmd_name, help='Manage and inspect project skills (list, suggest, add, remove)')
        sk.add_argument('action_or_project', nargs='?', default=None,
                        help='Action (list, suggest, add, remove) or project directory')
        sk.add_argument('target', nargs='?', default=None, help='Skill ID (for add/remove) or project directory')
        sk.add_argument('extra_project', nargs='?', default=None, help='Project directory when target is skill ID')
        sk.add_argument('--lang', choices=['en', 'pl'])
        sk.add_argument('--force', action='store_true', help='Force removal of local project skills')

    x = s.add_parser('run')
    x.add_argument('project', nargs='?', default='.')
    x.add_argument('prompt', nargs='?')
    x.add_argument('--prompt', dest='prompt_opt')
    x.add_argument('--worktree', action='store_true', help='Execute agent run inside an isolated git worktree')
    x.add_argument('--auto-merge', '--merge', dest='auto_merge', action='store_true', help='Automatically merge into target branch on success and delete temporary branch')
    x.add_argument('--auto-discard', '--discard', dest='auto_discard', action='store_true', help='Automatically discard changes and delete temporary branch')
    x.add_argument('--non-interactive', action='store_true', help='Do not prompt interactively after isolated run')
    x.add_argument('--no-auto-skills', action='store_true', help='Disable automatic and proactive skill provisioning by AI agents')
    x.add_argument('--solo', '--single-provider', dest='solo', action='store_true', default=None,
                   help='Run in solo mode with primaryProvider only (bypasses external reviewer CLI requirements)')
    x.add_argument('--availability-fallback', dest='availability_fallback', action='store_true', default=None,
                   help='Enable automatic fallback to isolated primaryProvider when reviewers fail or are missing')
    x.add_argument('--no-availability-fallback', dest='availability_fallback', action='store_false',
                   help='Disable automatic fallback to isolated primaryProvider')

    x = s.add_parser('resume')
    x.add_argument('run_id')
    x.add_argument('project', nargs='?', default='.')
    x.add_argument('--extra-rounds', dest='extra_rounds', type=int, default=0)

    x = s.add_parser('runs')
    x.add_argument('project', nargs='?', default='.')

    x = s.add_parser('review')
    x.add_argument('run_id', nargs='?', default='latest', help='Run ID to inspect (default: latest)')
    x.add_argument('project', nargs='?', default='.')
    x.add_argument('--diff', action='store_true', help='Display complete diff against base ref')
    x.add_argument('--merge', action='store_true', help='Merge the run branch into current branch')
    x.add_argument('--discard', action='store_true', help='Discard and delete the run branch')
    x.add_argument('--keep-branch', action='store_true', help='Keep temporary branch after merging instead of deleting it')

    x = s.add_parser('uninstall')
    x.add_argument('project', nargs='?', default='.')
    x.add_argument('--dry-run', action='store_true')

    for name in ('onboard', 'quickstart', 'setup'):
        x = s.add_parser(name, help='Automated one-command project onboarding and setup')
        x.add_argument('project', nargs='?', default='.')
        x.add_argument('--profile', default='auto')
        x.add_argument('--solo', action='store_true', default=None, help='Force solo mode (singleProvider)')
        x.add_argument('--multi', dest='solo', action='store_false', help='Force multi-provider mode')
        x.add_argument('--lang', choices=['en', 'pl'], default='pl')
        x.add_argument('--provider', choices=['agy', 'claude', 'codex'], default=None)
        x.add_argument('--no-commit', action='store_true', help='Skip automatic Git commit after setup')

    x = s.add_parser('audit', help='Run comprehensive 360° application audit (security, architecture, tests, ops)')
    x.add_argument('project', nargs='?', default='.')
    x.add_argument('--output', default='docs/AUDIT.md', help='Output audit report file path (default: docs/AUDIT.md)')
    x.add_argument('--sarif', nargs='?', const='docs/audit.sarif', default=None,
                   help='Export audit findings to SARIF 2.1.0 format for GitHub Code Scanning (default: docs/audit.sarif)')
    x.add_argument('--lang', choices=['en', 'pl'], default='pl', help='Language for audit prompt and report (default: pl)')
    x.add_argument('--worktree', action='store_true', default=True, help='Execute audit inside an isolated git worktree')
    x.add_argument('--no-worktree', dest='worktree', action='store_false', help='Execute directly without worktree')
    x.add_argument('--solo', '--single-provider', dest='solo', action='store_true', default=None,
                   help='Run in solo mode with primaryProvider only')
    x.add_argument('--auto-merge', '--merge', dest='auto_merge', action='store_true', help='Automatically merge audit report on success')

    x = s.add_parser('sarif', help='Convert audit findings markdown to SARIF 2.1.0 format for GitHub Code Scanning')
    x.add_argument('source', nargs='?', default='docs/AUDIT.md', help='Input audit markdown report (default: docs/AUDIT.md)')
    x.add_argument('--output', default='docs/audit.sarif', help='Output SARIF file path (default: docs/audit.sarif)')
    x.add_argument('project', nargs='?', default='.')

    return p

def main():
    a = parser().parse_args()
    project = Path(getattr(a, 'project', '.'))
    try:
        if a.command == 'profiles':
            print('\n'.join(sorted(x.stem for x in profiles_root().glob('*.json'))))
            return 0
        if a.command == 'resolve':
            resolve(project, a.file, a.strategy)
            return 0
        if a.command == 'install':
            lang = a.lang or 'en'
            profile = 'auto' if getattr(a, 'auto', False) else a.profile
            install(project, profile, lang)
            print(f'\nInstalled. Profile: {profile}, language: {lang}\nNext: ai-team doctor .')
            return 2 if status(project).get('conflicts') else 0
        if a.command == 'workflow':
            dest = install_workflow(project)
            print(f'GitHub Actions workflow installed: {dest.relative_to(project.resolve()).as_posix()}')
            print('Next: Commit .github/workflows/ai-team-update.yml to enable automated weekly PR updates.')
            return 0
        if a.command == 'gitignore':
            res = configure_gitignore(project, private=a.private)
            target = '.git/info/exclude (private)' if a.private else '.gitignore'
            if res == 'up-to-date':
                print(f'Git ignore rules in {target} are already up-to-date.')
            else:
                print(f'Git ignore rules successfully configured in {target}.')
            return 0
        if a.command == 'update':
            if getattr(a, 'check', False):
                from .utils import check_upstream_version, version_is_newer
                upstream = check_upstream_version()
                st = status(project)
                curr = st.get('frameworkVersion') if st.get('installed') else __version__
                if not upstream:
                    print(f'Current version: {curr}. Could not check upstream releases (offline or rate limited).')
                elif not version_is_newer(upstream, curr):
                    print(f'AI Engineering Team is up-to-date (version: {curr}).')
                else:
                    print(f'Update available: {curr} -> {upstream}')
                    print(f'Run: pip install --upgrade git+https://github.com/tomaasz/ai-engineering-team.git && ai-team update {project}')
                return 0
            c = update(project, a.profile, a.lang)
            print('\nUpdate complete.')
            print(f'Conflicts: {len(c)} — .ai-team/conflicts/' if c else 'No conflicts.')
            return 2 if c else 0
        if a.command == 'status':
            st = status(project, check_upstream=True)
            if not st['installed']:
                print('AI Engineering Team: not installed')
            else:
                print(f"Version: {st['frameworkVersion']}\nProfile: {st['profile']}\nLanguage: {st['language']}\nManaged files: {st['managedFiles']}\nConflicts: {st.get('conflicts', [])}")
                if st.get('upstreamVersion') and st.get('outdated'):
                    print(f"\n[UPDATE AVAILABLE] Newer version {st['upstreamVersion']} available on GitHub (installed: {st['frameworkVersion']}).")
                    print(f"To update: pip install --upgrade git+https://github.com/tomaasz/ai-engineering-team.git && ai-team update {project}")
            return 0
        if a.command in ('skill', 'skills'):
            # Parse action and project
            known_actions = {'list', 'suggest', 'add', 'remove'}
            if a.action_or_project in known_actions:
                action = a.action_or_project
                if action in ('add', 'remove'):
                    skill_id = a.target
                    proj_path = Path(a.extra_project or '.')
                else:
                    skill_id = None
                    proj_path = Path(a.target or '.')
            else:
                action = 'list'
                skill_id = None
                proj_path = Path(a.action_or_project or '.')

            lang = getattr(a, 'lang', None) or 'en'

            if action == 'list':
                data = list_skills(proj_path)
                print(f"Project Skills ({proj_path.resolve()}):")
                print(f"\nInstalled ({len(data['installed'])}):")
                if not data['installed']:
                    print("  (none installed)")
                for item in data['installed']:
                    desc = f" - {item['description']}" if item['description'] else ''
                    print(f"  [{item['status']:7}] {item['id']}{desc}")

                avail_not_inst = [x for x in data['available'] if not x['installed']]
                print(f"\nAvailable in Catalog ({len(avail_not_inst)}):")
                if not avail_not_inst:
                    print("  (all catalog skills installed)")
                for item in avail_not_inst:
                    desc = f" - {item['description']}" if item['description'] else ''
                    print(f"  [CATALOG] {item['id']}{desc}")
                return 0

            elif action == 'suggest':
                stack = detect_stack(proj_path)
                sugs = suggest_skills(proj_path, lang)
                is_pl = lang == 'pl'
                print(f"--- {'Analiza stosu technologicznego' if is_pl else 'Tech Stack Analysis'} ({proj_path.resolve()}) ---")
                print(f"  {'Języki' if is_pl else 'Languages'}:   {', '.join(stack['languages']) or 'none'}")
                print(f"  {'Bazy danych' if is_pl else 'Databases'}:   {', '.join(stack['databases']) or 'none'}")
                print(f"  {'Narzędzia' if is_pl else 'Tools'}:       {', '.join(stack['tools']) or 'none'}")
                print(f"  {'Sygnatury' if is_pl else 'Markers'}:     {', '.join(stack['markers']) or 'none'}")
                print(f"  {'Zalecany profil' if is_pl else 'Recommended profile'}: '{stack['recommended_profile']}'")
                print(f"\n--- {'Rekomendowane skille' if is_pl else 'Recommended Skills'} ---")
                for s_item in sugs:
                    st_tag = 'ZAINSTALOWANY' if is_pl and s_item['installed'] else ('INSTALLED' if s_item['installed'] else ('DOSTĘPNY' if is_pl else 'AVAILABLE'))
                    print(f"  [{st_tag:13}] {s_item['id']} - {s_item['reason']}")
                return 0

            elif action == 'add':
                if not skill_id:
                    raise RuntimeError("Missing skill ID. Usage: ai-team skill add <category/name> [project]")
                res = add_skill(proj_path, skill_id, lang)
                print(f"[ADDED] {res['id']}")
                for f in res['files']:
                    print(f"  + {f}")
                return 0

            elif action == 'remove':
                if not skill_id:
                    raise RuntimeError("Missing skill ID. Usage: ai-team skill remove <category/name> [project]")
                res = remove_skill(proj_path, skill_id, force=getattr(a, 'force', False))
                print(f"[REMOVED] {res['id']}")
                for f in res['removed']:
                    print(f"  - {f}")
                return 0

        if a.command == 'doctor':
            return doctor(project, a.probe, solo=getattr(a, 'solo', None))
        if a.command == 'run':
            prompt = a.prompt_opt or a.prompt or input('What should the AI Engineering Team do? ').strip()
            if not prompt:
                raise RuntimeError('Prompt is empty.')
            auto_skills = False if getattr(a, 'no_auto_skills', False) else None
            solo = getattr(a, 'solo', None)
            fallback = getattr(a, 'availability_fallback', None)
            return run_team(project, prompt, use_worktree=a.worktree, auto_merge=a.auto_merge,
                            auto_discard=a.auto_discard, non_interactive=a.non_interactive,
                            auto_skills=auto_skills, solo=solo, availability_fallback=fallback)
        if a.command == 'runs':
            return runs(project)
        if a.command == 'resume':
            return resume_team(project, a.run_id, a.extra_rounds)
        if a.command == 'review':
            action = 'diff' if a.diff else ('merge' if a.merge else ('discard' if a.discard else None))
            return review_run(project, a.run_id, action, keep_branch=a.keep_branch)
        if a.command == 'uninstall':
            rem, skip = uninstall(project, a.dry_run)
            [print(('[DRY] ' if a.dry_run else '') + '[REMOVE] ' + x) for x in rem]
            [print('[KEEP]   ' + x) for x in skip]
            return 0
        if a.command in ('onboard', 'quickstart', 'setup'):
            return onboard(project, profile_name=a.profile, solo=a.solo,
                           lang=a.lang, provider=a.provider, no_commit=a.no_commit)
        if a.command == 'audit':
            output_file = getattr(a, 'output', 'docs/AUDIT.md')
            sarif_file = getattr(a, 'sarif', None)
            sarif_part = f"\n- Eksport SARIF: Przygotuj również plik {sarif_file} w standardzie OASIS SARIF 2.1.0 ze wszystkimi znaleziskami." if sarif_file else ""
            sarif_part_en = f"\n- SARIF Export: Also generate {sarif_file} in OASIS SARIF 2.1.0 format with all findings." if sarif_file else ""
            prompt = (
                f"Przeprowadź kompletny, rygorystyczny audyt 360° aplikacji i przygotuj szczegółowy raport w {output_file}.\n"
                "Zakres audytu:\n"
                "1. ARCHITEKTURA I JAKOŚĆ KODU: modularność, granice domenowe, dług technologiczny, martwy kod, duplikacja.\n"
                "2. BEZPIECZEŃSTWO I PODATNOŚCI: OWASP Top 10, CWE, wycieki sekretów/kluczy, SQLi/Command injection, XSS, CSRF, SSRF, IDOR, nagłówki bezpieczeństwa, audyt zależności.\n"
                "3. NIEZAWODNOŚĆ I OBSŁUGA BŁĘDÓW: wyciszane wyjątki, unhandled rejections, wyścigi współbieżności, zarządzanie zasobami (wycieki pamięci, deskryptory).\n"
                "4. WYDAJNOŚĆ I BAZA DANYCH: pętle N+1 zapytań, brakujące indeksy, blokowanie pętli zdarzeń, optymalizacja pamięci podręcznej.\n"
                "5. TESTY I JAKOŚĆ: luki w pokryciu testami (ścieżki krytyczne i błędy), fałszywie pozytywne mocki.\n"
                "6. DEVOPS I KONTENERY: Dockerfile (multi-stage, non-root), logowanie strukturyzowane, healthchecki (/health), walidacja zmiennych środowiskowych.\n\n"
                "Struktura raportu:\n"
                "- Executive Summary (Ogólna ocena, stan zdrowia systemu).\n"
                "- Matryca Znalezisk: Tabela ze wszystkimi problemami [CRITICAL, HIGH, MEDIUM, LOW], lokalizacją plik:linia i zalecaną akcją.\n"
                "- Szczegółowa Analiza: Dowód w kodzie, wpływ oraz konkretny, minimalny kod naprawczy dla każdego problemu.\n"
                "- Plan Działań Naprawczych (Faza 1 P0, Faza 2 P1, Faza 3 P2)."
                f"{sarif_part}"
            )
            lang = getattr(a, 'lang', 'pl')
            if lang == 'en':
                prompt = (
                    f"Perform a comprehensive, rigorous 360° application audit and generate a detailed report in {output_file}.\n"
                    "Audit Scope:\n"
                    "1. ARCHITECTURE & CODE QUALITY: modularity, domain boundaries, technical debt, dead code, DRY violations.\n"
                    "2. SECURITY & VULNERABILITIES: OWASP Top 10, CWE, secret/key leaks, SQLi/Command injection, XSS, CSRF, SSRF, IDOR, security headers, dependency audit.\n"
                    "3. RELIABILITY & ERROR HANDLING: silent exceptions, unhandled rejections, race conditions, resource cleanup (memory leaks, open descriptors).\n"
                    "4. PERFORMANCE & DATABASE: N+1 queries, missing indexes, event loop blocking, cache optimization.\n"
                    "5. TESTING & QUALITY: test coverage gaps (critical flows and error paths), mock validity and edge cases.\n"
                    "6. DEVOPS & CONTAINERS: Dockerfile hygiene (multi-stage, non-root), structured logging, health checks (/health), environment variable validation.\n\n"
                    "Report Structure:\n"
                    "- Executive Summary (System health score, overall maturity).\n"
                    "- Findings Matrix: Markdown table with all findings [CRITICAL, HIGH, MEDIUM, LOW], file:line location, and recommended action.\n"
                    "- Deep-Dive Analysis: Proof in code, security/stability impact, and minimal actionable code fix for every finding.\n"
                    "- Remediation Action Plan (Phase 1 P0 immediate blockers, Phase 2 P1, Phase 3 P2 backlog)."
                    f"{sarif_part_en}"
                )
            else:
                prompt = (
                    f"Przeprowadź kompletny, rygorystyczny audyt 360° aplikacji i przygotuj szczegółowy raport w {output_file}.\n"
                    "Zakres audytu:\n"
                    "1. ARCHITEKTURA I JAKOŚĆ KODU: modularność, granice domenowe, dług technologiczny, martwy kod, duplikacja.\n"
                    "2. BEZPIECZEŃSTWO I PODATNOŚCI: OWASP Top 10, CWE, wycieki sekretów/kluczy, SQLi/Command injection, XSS, CSRF, SSRF, IDOR, nagłówki bezpieczeństwa, audyt zależności.\n"
                    "3. NIEZAWODNOŚĆ I OBSŁUGA BŁĘDÓW: wyciszane wyjątki, unhandled rejections, wyścigi współbieżności, zarządzanie zasobami (wycieki pamięci, deskryptory).\n"
                    "4. WYDAJNOŚĆ I BAZA DANYCH: pętle N+1 zapytań, brakujące indeksy, blokowanie pętli zdarzeń, optymalizacja pamięci podręcznej.\n"
                    "5. TESTY I JAKOŚĆ: luki w pokryciu testami (ścieżki krytyczne i błędy), fałszywie pozytywne mocki.\n"
                    "6. DEVOPS I KONTENERY: Dockerfile (multi-stage, non-root), logowanie strukturyzowane, healthchecki (/health), walidacja zmiennych środowiskowych.\n\n"
                    "Struktura raportu:\n"
                    "- Executive Summary (Ogólna ocena, stan zdrowia systemu).\n"
                    "- Matryca Znalezisk: Tabela ze wszystkimi problemami [CRITICAL, HIGH, MEDIUM, LOW], lokalizacją plik:linia i zalecaną akcją.\n"
                    "- Szczegółowa Analiza: Dowód w kodzie, wpływ oraz konkretny, minimalny kod naprawczy dla każdego problemu.\n"
                    "- Plan Działań Naprawczych (Faza 1 P0, Faza 2 P1, Faza 3 P2)."
                    f"{sarif_part}"
                )
            auto_skills = False if getattr(a, 'no_auto_skills', False) else None
            solo = getattr(a, 'solo', None)
            ret = run_team(project, prompt, use_worktree=a.worktree, auto_merge=a.auto_merge,
                           auto_discard=False, non_interactive=False,
                           auto_skills=auto_skills, solo=solo, availability_fallback=True)
            if sarif_file:
                sarif_path = project / sarif_file
                out_path = project / output_file
                if (not sarif_path.exists() or sarif_path.stat().st_size == 0) and out_path.exists():
                    try:
                        export_sarif(out_path, sarif_path)
                        print(f"Wyeksportowano raport SARIF 2.1.0 do {sarif_file}")
                    except Exception as sarif_err:
                        print(f"Ostrzeżenie: Nie udało się wyeksportować SARIF: {sarif_err}", file=sys.stderr)
            return ret
        if a.command == 'sarif':
            source_file = getattr(a, 'source', 'docs/AUDIT.md')
            out_file = getattr(a, 'output', 'docs/audit.sarif')
            src_path = project / source_file
            out_path = project / out_file
            if not src_path.exists():
                print(f"BŁĄD: Plik źródłowy raportu nie istnieje: {src_path}", file=sys.stderr)
                return 1
            exported = export_sarif(src_path, out_path)
            print(f"Wyeksportowano raport SARIF 2.1.0 do {exported}")
            return 0
    except Exception as e:
        print('ERROR:', e, file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
