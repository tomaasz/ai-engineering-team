import argparse, sys
from pathlib import Path
from .installer import install,update,status,uninstall,resolve
from .runner import run_team,doctor,resume_team,runs
from .utils import profiles_root
from . import __version__

def parser():
    p=argparse.ArgumentParser(prog='ai-team'); p.add_argument('--version', action='version', version=__version__); s=p.add_subparsers(dest='command',required=True)
    s.add_parser('profiles')
    x=s.add_parser('install'); x.add_argument('project',nargs='?',default='.'); x.add_argument('--profile',default='core'); x.add_argument('--lang',choices=['en','pl'])
    x=s.add_parser('update'); x.add_argument('project',nargs='?',default='.'); x.add_argument('--profile'); x.add_argument('--lang',choices=['en','pl'])
    x=s.add_parser('status'); x.add_argument('project',nargs='?',default='.')
    x=s.add_parser('doctor'); x.add_argument('project',nargs='?',default='.'); x.add_argument('--probe',action='store_true')
    x=s.add_parser('resolve'); x.add_argument('project'); x.add_argument('file'); x.add_argument('--strategy',choices=['keep','upstream'],required=True)
    x=s.add_parser('run'); x.add_argument('project',nargs='?',default='.'); x.add_argument('prompt',nargs='?'); x.add_argument('--prompt',dest='prompt_opt')
    x=s.add_parser('resume'); x.add_argument('run_id'); x.add_argument('project',nargs='?',default='.'); x.add_argument('--extra-rounds',dest='extra_rounds',type=int,default=0)
    x=s.add_parser('runs'); x.add_argument('project',nargs='?',default='.')
    x=s.add_parser('uninstall'); x.add_argument('project',nargs='?',default='.'); x.add_argument('--dry-run',action='store_true')
    return p

def main():
    a=parser().parse_args(); project=Path(getattr(a,'project','.'))
    try:
        if a.command=='profiles':
            print('\n'.join(sorted(x.stem for x in profiles_root().glob('*.json')))); return 0
        if a.command=='resolve': resolve(project,a.file,a.strategy); return 0
        if a.command=='install':
            lang=a.lang or 'en'; install(project,a.profile,lang)
            print(f'\nInstalled. Profile: {a.profile}, language: {lang}\nNext: ai-team doctor .')
            return 2 if status(project).get('conflicts') else 0
        if a.command=='update':
            c=update(project,a.profile,a.lang); print('\nUpdate complete.'); print(f'Conflicts: {len(c)} — .ai-team/conflicts/' if c else 'No conflicts.'); return 2 if c else 0
        if a.command=='status':
            st=status(project); print('AI Engineering Team: not installed' if not st['installed'] else f"Version: {st['frameworkVersion']}\nProfile: {st['profile']}\nLanguage: {st['language']}\nManaged files: {st['managedFiles']}\nConflicts: {st.get('conflicts',[])}"); return 0
        if a.command=='doctor': return doctor(project,a.probe)
        if a.command=='run':
            prompt=a.prompt_opt or a.prompt or input('What should the AI Engineering Team do? ').strip()
            if not prompt: raise RuntimeError('Prompt is empty.')
            return run_team(project,prompt)
        if a.command=='runs': return runs(project)
        if a.command=='resume': return resume_team(project,a.run_id,a.extra_rounds)
        if a.command=='uninstall':
            rem,skip=uninstall(project,a.dry_run); [print(('[DRY] ' if a.dry_run else '')+'[REMOVE] '+x) for x in rem]; [print('[KEEP]   '+x) for x in skip]; return 0
    except Exception as e: print('ERROR:',e,file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
