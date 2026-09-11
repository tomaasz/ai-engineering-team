from pathlib import Path
import hashlib, json, re, shutil, subprocess

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def run(cmd, cwd=None, capture=False, check=True, timeout=None):
    kw = {'cwd': str(cwd) if cwd else None, 'text': True, 'timeout': timeout}
    if capture:
        kw.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p = subprocess.run(cmd, **kw)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}\n{getattr(p,'stderr','') or ''}")
    return p

def which(name): return shutil.which(name)
def load_json(path: Path): return json.loads(path.read_text(encoding='utf-8'))
def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def package_root(): return Path(__file__).resolve().parent
def template_root(): return package_root()/'templates'
def profiles_root(): return package_root()/'profiles'
def ensure_git_repo(project: Path):
    p = run(['git','rev-parse','--show-toplevel'], cwd=project, capture=True, check=False)
    if p.returncode != 0: raise RuntimeError(f'{project} nie jest repozytorium Git.')
    return Path(p.stdout.strip()).resolve()
def safe_slug(text, max_len=44):
    text = text.lower().translate(str.maketrans('ąćęłńóśźż','acelnoszz'))
    s = re.sub(r'[^a-z0-9._-]+','-',text).strip('-')
    return (s[:max_len].rstrip('-') or 'task')
