from pathlib import Path
import shutil
from . import __version__
from .utils import sha256_file, save_json, load_json, template_root, profiles_root

VERSION='3.0.0'; STATE_DIR='.ai-team'; STATE_FILE='state.json'
VERSION = __version__; STATE_DIR = '.ai-team'; STATE_FILE = 'state.json'
LOCAL_FILES={'PROJECT_CONTEXT.md','ai-team.config.json'}
LOCAL_PREFIXES={'.agents/skills/project/'}
def _is_local(rel): return rel in LOCAL_FILES or any(rel.startswith(p) for p in LOCAL_PREFIXES)
def _profile(name):
    p=profiles_root()/f'{name}.json'
    if not p.exists():
        avail=', '.join(sorted(x.stem for x in profiles_root().glob('*.json')))
        raise RuntimeError(f"Nieznany profil '{name}'. Dostępne: {avail}")
    return load_json(p)
def _all_files():
    base=template_root(); return {p.relative_to(base).as_posix():p for p in base.rglob('*') if p.is_file()}
def _selected(profile):
    inc=profile.get('include',[]); exc=profile.get('exclude',[]); out={}
    for rel,src in _all_files().items():
        if inc and not any(rel==x or rel.startswith(x.rstrip('/')+'/') for x in inc): continue
        if any(rel==x or rel.startswith(x.rstrip('/')+'/') for x in exc): continue
        out[rel]=src
    return out
def _state(project):
    p=project/STATE_DIR/STATE_FILE
    return load_json(p) if p.exists() else None
def _save(project, profile, managed): save_json(project/STATE_DIR/STATE_FILE, {'frameworkVersion':VERSION,'profile':profile,'managed':managed})
def _merge_tasks(project, template):
    dest=project/'.vscode/tasks.json'; new=load_json(template)
    if not dest.exists(): dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(template,dest); return 'created'
    try: old=load_json(dest)
    except Exception:
        conflict=project/STATE_DIR/'conflicts/.vscode/tasks.ai-team.json'; conflict.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(template,conflict); return f'conflict:{conflict}'
    labels={x.get('label') for x in old.setdefault('tasks',[]) if isinstance(x,dict)}
    for task in new.get('tasks',[]):
        if task.get('label') not in labels: old['tasks'].append(task)
    ids={x.get('id') for x in old.setdefault('inputs',[]) if isinstance(x,dict)}
    for item in new.get('inputs',[]):
        if item.get('id') not in ids: old['inputs'].append(item)
    save_json(dest,old); return 'merged'
def install(project:Path, profile_name:str):
    project=project.resolve(); files=_selected(_profile(profile_name)); managed={}
    for rel,src in sorted(files.items()):
        if rel=='.vscode/tasks.json':
            st=_merge_tasks(project,src); dest=project/rel
            if dest.exists(): managed[rel]=sha256_file(dest)
            print(f'[VSCode] {st}'); continue
        dest=project/rel
        if _is_local(rel) and dest.exists(): print(f'[KEEP] {rel}'); continue
        dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dest)
        if _is_local(rel): print(f'[INIT] {rel}')
        else: managed[rel]=sha256_file(dest); print(f'[ADD]  {rel}')
    (project/'.ai/runs').mkdir(parents=True,exist_ok=True)
    ign=project/'.ai/.gitignore'
    if not ign.exists(): ign.write_text('runs/\nlatest.txt\n',encoding='utf-8')
    _save(project,profile_name,managed); return managed
def update(project:Path):
    project=project.resolve(); state=_state(project)
    if not state: raise RuntimeError('Framework nie jest zainstalowany.')
    files=_selected(_profile(state['profile'])); old=state.get('managed',{}); new={}; conflicts=[]
    for rel,src in sorted(files.items()):
        if _is_local(rel):
            dest=project/rel
            if not dest.exists(): dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dest); print(f'[INIT] {rel}')
            else: print(f'[KEEP] {rel}')
            continue
        if rel=='.vscode/tasks.json':
            st=_merge_tasks(project,src); dest=project/rel
            if dest.exists(): new[rel]=sha256_file(dest)
            print(f'[VSCode] {st}'); continue
        dest=project/rel; old_hash=old.get(rel)
        if not dest.exists(): dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dest); new[rel]=sha256_file(dest); print(f'[ADD]  {rel}'); continue
        current=sha256_file(dest)
        if old_hash is None or current!=old_hash:
            conflict=project/STATE_DIR/'conflicts'/rel; conflict.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,conflict)
            new[rel]=current; conflicts.append(rel); print(f'[CONFLICT] {rel} -> {conflict.relative_to(project)}')
        else: shutil.copy2(src,dest); new[rel]=sha256_file(dest); print(f'[UPD]  {rel}')
    _save(project,state['profile'],new); return conflicts
def status(project:Path):
    st=_state(project.resolve())
    return {'installed':False} if not st else {'installed':True,'frameworkVersion':st.get('frameworkVersion'),'profile':st.get('profile'),'managedFiles':len(st.get('managed',{}))}
def uninstall(project:Path,dry_run=False):
    project=project.resolve(); st=_state(project)
    if not st: raise RuntimeError('Framework nie jest zainstalowany.')
    removed=[]; skipped=[]
    for rel,old_hash in st.get('managed',{}).items():
        if rel=='.vscode/tasks.json': skipped.append(rel); continue
        dest=project/rel
        if not dest.exists(): continue
        if sha256_file(dest)!=old_hash: skipped.append(rel); continue
        removed.append(rel)
        if not dry_run: dest.unlink()
    if not dry_run:
        sp=project/STATE_DIR/STATE_FILE
        if sp.exists(): sp.unlink()
    return removed,skipped
