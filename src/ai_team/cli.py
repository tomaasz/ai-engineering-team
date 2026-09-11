import argparse, sys
from pathlib import Path
from .installer import install,update,status,uninstall
from .runner import run_team,doctor,_load_manifest,_validate_resume_context

def resume_team(project, run_id):
    project = Path(project).resolve()
    if run_id == 'latest':
        marker = project / '.ai/latest.txt'
        if not marker.exists(): raise RuntimeError('run manifest missing: latest marker')
        run_id = marker.read_text(encoding='utf-8').strip()
    manifest = _load_manifest(project, run_id)
    _validate_resume_context(project, manifest)
    raise RuntimeError('resume is conservative: failed stages must be re-run explicitly; no safe automatic retry available')


def _resume_args(x):
    x.add_argument('run_id'); x.add_argument('project', nargs='?', default='.')
    return x


def parser():
    p=argparse.ArgumentParser(prog='ai-team'); s=p.add_subparsers(dest='command',required=True)
    x=s.add_parser('install'); x.add_argument('project',nargs='?',default='.'); x.add_argument('--profile',default='core')
    x=s.add_parser('update'); x.add_argument('project',nargs='?',default='.')
    x=s.add_parser('status'); x.add_argument('project',nargs='?',default='.')
    x=s.add_parser('doctor'); x.add_argument('project',nargs='?',default='.'); x.add_argument('--deep',action='store_true',help='sprawdź działanie CLI przez --version')
    x=s.add_parser('run'); x.add_argument('project',nargs='?',default='.'); x.add_argument('prompt',nargs='?'); x.add_argument('--prompt',dest='prompt_opt')
    _resume_args(s.add_parser('resume'))
    x=s.add_parser('uninstall'); x.add_argument('project',nargs='?',default='.'); x.add_argument('--dry-run',action='store_true')
    return p

def main():
    a=parser().parse_args(); project=Path(a.project)
    try:
        if a.command=='install': install(project,a.profile); print(f'\nZainstalowano. Profil: {a.profile}\nNastępnie: ai-team doctor .'); return 0
        if a.command=='update':
            c=update(project); print('\nAktualizacja zakończona.'); print(f'Konflikty: {len(c)} — .ai-team/conflicts/' if c else 'Brak konfliktów.'); return 0
        if a.command=='status':
            st=status(project); print('AI Engineering Team: nie zainstalowany' if not st['installed'] else f"Version: {st['frameworkVersion']}\nProfile: {st['profile']}\nManaged files: {st['managedFiles']}"); return 0
        if a.command=='doctor': return doctor(project, deep=a.deep)
        if a.command=='resume': return resume_team(a.project, a.run_id)
        if a.command=='run':
            prompt=a.prompt_opt or a.prompt or input('Co ma zrobić AI Engineering Team? ').strip()
            if not prompt: raise RuntimeError('Prompt jest pusty.')
            return run_team(project,prompt)
        if a.command=='uninstall':
            rem,skip=uninstall(project,a.dry_run); [print(('[DRY] ' if a.dry_run else '')+'[REMOVE] '+x) for x in rem]; [print('[KEEP]   '+x) for x in skip]; return 0
    except Exception as e: print('ERROR:',e,file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
