import argparse, sys
from pathlib import Path
from .installer import install, update, status, uninstall, resolve
from .runner import run_team, doctor, resume_team, runs, review_run
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

    x = s.add_parser('run')
    x.add_argument('project', nargs='?', default='.')
    x.add_argument('prompt', nargs='?')
    x.add_argument('--prompt', dest='prompt_opt')
    x.add_argument('--worktree', action='store_true', help='Execute agent run inside an isolated git worktree')
    x.add_argument('--auto-merge', '--merge', dest='auto_merge', action='store_true', help='Automatically merge into target branch on success and delete temporary branch')
    x.add_argument('--auto-discard', '--discard', dest='auto_discard', action='store_true', help='Automatically discard changes and delete temporary branch')
    x.add_argument('--non-interactive', action='store_true', help='Do not prompt interactively after isolated run')

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
            install(project, a.profile, lang)
            print(f'\nInstalled. Profile: {a.profile}, language: {lang}\nNext: ai-team doctor .')
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
        if a.command == 'doctor':
            return doctor(project, a.probe)
        if a.command == 'run':
            prompt = a.prompt_opt or a.prompt or input('What should the AI Engineering Team do? ').strip()
            if not prompt:
                raise RuntimeError('Prompt is empty.')
            return run_team(project, prompt, use_worktree=a.worktree)
            return run_team(project, prompt, use_worktree=a.worktree, auto_merge=a.auto_merge,
                            auto_discard=a.auto_discard, non_interactive=a.non_interactive)
        if a.command == 'runs':
            return runs(project)
        if a.command == 'resume':
            return resume_team(project, a.run_id, a.extra_rounds)
        if a.command == 'review':
            action = 'diff' if a.diff else ('merge' if a.merge else ('discard' if a.discard else None))
            return review_run(project, a.run_id, action)
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
