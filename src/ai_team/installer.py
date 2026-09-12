from pathlib import Path
import shutil
from . import __version__
from .utils import sha256_file, save_json, load_json, load_jsonc, template_root, profiles_root, ensure_git_repo, project_path

VERSION = __version__; STATE_DIR = '.ai-team'; STATE_FILE = 'state.json'
LOCAL_FILES={'PROJECT_CONTEXT.md','ai-team.config.json'}
LOCAL_PREFIXES={'.agents/skills/project/'}
def _is_local(rel): return rel in LOCAL_FILES or any(rel.startswith(p) for p in LOCAL_PREFIXES)
def _profile(name):
    if name not in {x.stem for x in profiles_root().glob('*.json')}:
        raise RuntimeError(f"Nieznany profil '{name}'. Dostępne: {', '.join(sorted(x.stem for x in profiles_root().glob('*.json')))}")
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
    p=project_path(project,STATE_DIR+'/'+STATE_FILE)
    return load_json(p) if p.exists() else None
def _save(project, profile, managed, conflicts=(), kept=()):
    save_json(project_path(project, STATE_DIR+'/'+STATE_FILE), {'frameworkVersion':VERSION,'profile':profile,'managed':managed, 'conflicts':list(conflicts), 'kept':list(kept)})
def _merge_tasks(project, template):
    dest=project_path(project,'.vscode/tasks.json'); new=load_json(template)
    ownership=project_path(project,STATE_DIR+'/vscode-state.json')
    if not dest.exists():
        dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(template,dest)
        save_json(ownership,new)
        return 'created'
    try:
        old=load_jsonc(dest)
        if not isinstance(old,dict): raise ValueError('Expected object')
        for key in ('tasks','inputs'):
            if not isinstance(old.get(key,[]),list) or any(not isinstance(x,dict) for x in old.get(key,[])):
                raise ValueError('Expected array of objects')
    except Exception:
        conflict=project_path(project,STATE_DIR+'/conflicts/.vscode/tasks.ai-team.json'); conflict.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(template,conflict); return f'conflict:{conflict}'
    baseline=load_json(ownership) if ownership.exists() else {}
    managed={}; conflict_found=False
    for key,identifier in [('tasks','label'),('inputs','id')]:
        existing=old.setdefault(key,[])
        previous={x[identifier]:x for x in baseline.get(key,[]) if identifier in x}
        managed[key]=list(previous.values())
        for item in new.get(key,[]):
            matches=[i for i,x in enumerate(existing) if x.get(identifier)==item[identifier]]
            if not matches:
                existing.append(item)
            elif len(matches)==1 and existing[matches[0]]==previous.get(item[identifier]):
                existing[matches[0]]=item
            elif len(matches)==1 and existing[matches[0]]==item:
                # Identical user-owned entries stay user-owned.
                continue
            else:
                conflict_found=True; continue
            managed[key]=[x for x in managed[key] if x[identifier]!=item[identifier]]+[item]
    if conflict_found:
        conflict=project_path(project,STATE_DIR+'/conflicts/.vscode/tasks.ai-team.json')
        conflict.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(template,conflict)
    backup=project_path(project,STATE_DIR+'/backups/tasks.json.original')
    if not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(dest,backup)
    save_json(dest,old); save_json(ownership,managed)
    return f'conflict:{conflict}' if conflict_found else 'merged'
def install(project:Path, profile_name:str):
    project=ensure_git_repo(project.resolve()); files=_selected(_profile(profile_name)); managed={}; conflicts=[]
    if _state(project):
        update(project, profile_name)
        return _state(project)['managed']
    for rel in files:
        project_path(project,rel)
        project_path(project,STATE_DIR+'/conflicts/'+rel)
    project_path(project,'.ai/runs')
    project_path(project,'.ai/.gitignore')
    for rel,src in sorted(files.items()):
        if rel=='.vscode/tasks.json':
            st=_merge_tasks(project,src); dest=project/rel
            if dest.exists(): managed[rel]=sha256_file(dest)
            if st.startswith('conflict:'): conflicts.append(rel)
            print(f'[VSCode] {st}'); continue
        dest=project_path(project,rel)
        if _is_local(rel) and dest.exists(): print(f'[KEEP] {rel}'); continue
        if dest.exists():
            conflict=project_path(project,STATE_DIR+'/conflicts/'+rel)
            conflict.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,conflict)
            managed[rel]=None; conflicts.append(rel); print(f'[KEEP/CONFLICT] {rel}'); continue
        dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dest)
        if _is_local(rel): print(f'[INIT] {rel}')
        else: managed[rel]=sha256_file(dest); print(f'[ADD]  {rel}')
    (project/'.ai/runs').mkdir(parents=True,exist_ok=True)
    ign=project/'.ai/.gitignore'
    if not ign.exists(): ign.write_text('runs/\nlatest.txt\n',encoding='utf-8')
    _save(project,profile_name,managed,conflicts); return managed
def update(project:Path, profile_name=None):
    project=project.resolve()
    try: project=ensure_git_repo(project)
    except RuntimeError: pass
    state=_state(project)
    if not state: raise RuntimeError('Framework nie jest zainstalowany.')
    profile_name=profile_name or state['profile']
    files=_selected(_profile(profile_name)); old=state.get('managed',{}); new=dict(old); conflicts=[]
    kept=state.get('kept',[])
    for rel in files:
        project_path(project,rel)
        project_path(project,STATE_DIR+'/conflicts/'+rel)
    for rel,src in sorted(files.items()):
        if rel in kept: continue
        if _is_local(rel):
            dest=project_path(project,rel)
            if not dest.exists(): dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dest); print(f'[INIT] {rel}')
            else: print(f'[KEEP] {rel}')
            continue
        if rel=='.vscode/tasks.json':
            st=_merge_tasks(project,src); dest=project/rel
            if dest.exists(): new[rel]=sha256_file(dest)
            if st.startswith('conflict:'): conflicts.append(rel)
            print(f'[VSCode] {st}'); continue
        dest=project_path(project,rel); old_hash=old.get(rel)
        if not dest.exists(): dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dest); new[rel]=sha256_file(dest); print(f'[ADD]  {rel}'); continue
        current=sha256_file(dest)
        if current==sha256_file(src) and old_hash is not None:
            new[rel]=current
        elif old_hash is None or current!=old_hash:
            conflict=project_path(project,STATE_DIR+'/conflicts/'+rel); conflict.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,conflict)
            new[rel]=old_hash; conflicts.append(rel); print(f'[CONFLICT] {rel} -> {conflict.relative_to(project)}')
        else: shutil.copy2(src,dest); new[rel]=sha256_file(dest); print(f'[UPD]  {rel}')
    # Retired templates remain tracked, including unresolved retired conflicts.
    conflicts.extend(x for x in state.get('conflicts',[]) if x not in files and x not in kept)
    _save(project,profile_name,new,conflicts,kept); return conflicts
def status(project:Path):
    project=project.resolve()
    try: project=ensure_git_repo(project)
    except RuntimeError: pass
    st=_state(project)
    return {'installed':False} if not st else {'installed':True,'frameworkVersion':st.get('frameworkVersion'),'profile':st.get('profile'),'managedFiles':len(st.get('managed',{})), 'conflicts':st.get('conflicts',[])}
def uninstall(project:Path,dry_run=False):
    project=project.resolve()
    try: project=ensure_git_repo(project)
    except RuntimeError: pass
    st=_state(project)
    if not st: raise RuntimeError('Framework nie jest zainstalowany.')
    removed=[]; skipped=[]
    for rel,old_hash in st.get('managed',{}).items():
        if rel=='.vscode/tasks.json' or rel in st.get('kept',[]) or rel in st.get('conflicts',[]): skipped.append(rel); continue
        dest=project_path(project,rel)
        if not dest.exists(): continue
        if sha256_file(dest)!=old_hash: skipped.append(rel); continue
        removed.append(rel)
        if not dry_run: dest.unlink()
    if not dry_run:
        sp=project/STATE_DIR/STATE_FILE
        if sp.exists(): sp.unlink()
    return removed,skipped


def resolve(project:Path, relative:str, strategy='keep'):
    project=ensure_git_repo(project.resolve()); state=_state(project)
    if not state or relative not in state.get('conflicts',[]):
        raise RuntimeError('No recorded conflict for this path')
    if strategy not in {'keep','upstream'}:
        raise ValueError('strategy must be keep or upstream')
    dest=project_path(project,relative)
    conflict_rel='.vscode/tasks.ai-team.json' if relative=='.vscode/tasks.json' else relative
    source=project_path(project,STATE_DIR+'/conflicts/'+conflict_rel)
    if strategy=='keep':
        if not dest.exists(): raise RuntimeError('Cannot keep a missing file')
        state.setdefault('kept',[]).append(relative)
        state['managed'].pop(relative,None)
    else:
        # Explicit resolution is the only operation that replaces a customized file.
        backup=project_path(project,STATE_DIR+'/backups/'+relative)
        if dest.exists() and not backup.exists():
            backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(dest,backup)
        dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,dest)
        state['managed'][relative]=sha256_file(dest)
        if relative=='.vscode/tasks.json':
            save_json(project_path(project,STATE_DIR+'/vscode-state.json'),load_json(source))
    state['conflicts'].remove(relative)
    _save(project,state['profile'],state['managed'],state['conflicts'],state.get('kept',[]))
    if source.exists(): source.unlink()
