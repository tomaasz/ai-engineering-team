import argparse, sys
from pathlib import Path
from .installer import install, update, status, uninstall, resolve
from .runner import run_team, doctor, resume_team, runs, review_run
from .skills import list_skills, suggest_skills, add_skill, remove_skill, detect_stack
from .utils import profiles_root
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

    x = s.add_parser('update')
    x.add_argument('project', nargs='?', default='.')
    x.add_argument('--profile')
    x.add_argument('--lang', choices=['en', 'pl'])

    x = s.add_parser('status')
    x.add_argument('project', nargs='?', default='.')

    x = s.add_parser('doctor')
    x.add_argument('project', nargs='?', default='.')
    x.add_argument('--probe', action='store_true')

    x = s.add_parser('resolve')
    x.add_argument('project')
    x.add_argument('file')
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
        if a.command == 'update':
            c = update(project, a.profile, a.lang)
            print('\nUpdate complete.')
            print(f'Conflicts: {len(c)} — .ai-team/conflicts/' if c else 'No conflicts.')
            return 2 if c else 0
        if a.command == 'status':
            st = status(project)
            print('AI Engineering Team: not installed' if not st['installed'] else
                  f"Version: {st['frameworkVersion']}\nProfile: {st['profile']}\nLanguage: {st['language']}\nManaged files: {st['managedFiles']}\nConflicts: {st.get('conflicts', [])}")
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
            return doctor(project, a.probe)
        if a.command == 'run':
            prompt = a.prompt_opt or a.prompt or input('What should the AI Engineering Team do? ').strip()
            if not prompt:
                raise RuntimeError('Prompt is empty.')
            auto_skills = False if getattr(a, 'no_auto_skills', False) else None
            return run_team(project, prompt, use_worktree=a.worktree, auto_merge=a.auto_merge,
                            auto_discard=a.auto_discard, non_interactive=a.non_interactive,
                            auto_skills=auto_skills)
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
    except Exception as e:
        print('ERROR:', e, file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
