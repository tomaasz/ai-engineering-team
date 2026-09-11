from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, re, subprocess, sys, time
from .utils import run, which, load_json, save_json, ensure_git_repo, safe_slug

_SECRET_RE = re.compile(r'(KEY|TOKEN|SECRET|PASSWORD|PASS|COOKIE|CREDENTIAL)', re.I)

def _sanitized_env(allowlist=()):
    env = {k: v for k, v in os.environ.items() if not _SECRET_RE.search(k)}
    for key in allowlist:
        if key in os.environ and not _SECRET_RE.search(key):
            env[key] = os.environ[key]
    env['AI_TEAM_SUBPROCESS'] = '1'
    return env

def _now(): return datetime.now(timezone.utc).isoformat()
def _load_manifest(project, run_id):
    path = Path(project) / '.ai' / 'runs' / run_id / 'run.json'
    if not path.exists(): raise RuntimeError(f'run manifest missing: {path}')
    return load_json(path)

def _validate_resume_context(project, manifest):
    try: project = ensure_git_repo(Path(project).resolve())
    except RuntimeError as exc: raise RuntimeError(f'unsafe branch/base context: {exc}') from exc
    branch = _git(project, 'branch', '--show-current').stdout.strip()
    if branch != manifest.get('branch'):
        raise RuntimeError(f'unsafe branch context: expected {manifest.get("branch")}, got {branch}')
    base = _git(project, 'rev-parse', 'HEAD').stdout.strip()
    if base != manifest.get('base_ref'): raise RuntimeError('unsafe base context')
    if _git(project, 'status', '--porcelain').stdout.strip(): raise RuntimeError('unsafe working tree context')
    return project

def _write_trace(path, record):
    with path.open('a', encoding='utf-8') as f: f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')

def _stage_capture(stage, manifest, manifest_path, trace_path, cmd, cwd, out, err, allow_failure=False, repo_root=None):
    started, start = _now(), time.monotonic()
    entry = manifest['stages'].setdefault(stage, {'status':'pending'})
    entry.update(status='running', started_at=started); save_json(manifest_path, manifest)
    status, rc, error = 'succeeded', None, None
    try:
        try:
            rc = _capture(cmd, cwd, out, err, allow_failure=allow_failure, repo_root=repo_root)
        except TypeError as exc:
            if 'repo_root' not in str(exc): raise
            rc = _capture(cmd, cwd, out, err, allow_failure=allow_failure)
        if rc != 0: status = 'failed'
    except Exception as exc:
        status = 'failed'; error = {'class': type(exc).__name__, 'message': str(exc)}
    finished = _now(); entry.update(status=status, finished_at=finished, return_code=rc, artifact=out.name)
    if error: entry['error'] = error
    save_json(manifest_path, manifest)
    _write_trace(trace_path, {'stage':stage,'status':status,'started_at':started,'finished_at':finished,
        'duration_ms':round((time.monotonic()-start)*1000),'return_code':rc,'artifact':out.name,'error':error})
    if status == 'failed' and not allow_failure: raise RuntimeError(f'{stage} failed; see {err}')
    return rc

def _record_stage(manifest, manifest_path, trace_path, stage, artifact, status='succeeded', return_code=None):
    now = _now(); entry = manifest['stages'].setdefault(stage, {})
    entry.update(status=status, started_at=entry.get('started_at', now), finished_at=now, return_code=return_code, artifact=str(artifact))
    save_json(manifest_path, manifest)
    _write_trace(trace_path, {'stage':stage,'status':status,'started_at':entry['started_at'],'finished_at':now,'duration_ms':0,'return_code':return_code,'artifact':str(artifact),'error':None})

def _eval_artifact(manifest, path, diff_check):
    reasons=[]
    if not {'triage','primary','verifier'}.issubset(manifest['stages']): reasons.append('required stages missing')
    if diff_check != 0: reasons.append('diff-check failed')
    if manifest.get('final_verdict') not in {'PASS','PASS_WITH_NOTES'}: reasons.append('verdict not passing')
    save_json(path, {'passed':not reasons,'reasons':reasons,'verdict':manifest.get('final_verdict'),'diff_check':diff_check})

def _capture(cmd, cwd, out, err, allow_failure=False, timeout=3600, repo_root=None, env_allowlist=()):
    cwd = Path(cwd).resolve()
    if repo_root is not None:
        root = Path(repo_root).resolve()
        try: cwd.relative_to(root)
        except ValueError: raise RuntimeError(f'cwd outside repository root: {cwd}')
    if not cwd.exists() or not cwd.is_dir():
        raise RuntimeError(f'cwd outside repository root or missing: {cwd}')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8') as fo, err.open('w', encoding='utf-8') as fe:
        try:
            p=subprocess.run(cmd,cwd=str(cwd),text=True,stdout=fo,stderr=fe,timeout=timeout,
                env=_sanitized_env(env_allowlist),start_new_session=(sys.platform != 'win32'))
        except subprocess.TimeoutExpired as exc:
            fe.write(f'Process timeout after {timeout}s: {exc}\n')
            raise RuntimeError(f'Polecenie przekroczyło timeout {timeout}s. Log: {err}') from exc
    if p.returncode and not allow_failure: raise RuntimeError(f'Polecenie zakończone kodem {p.returncode}. Log: {err}')
    return p.returncode

def _git(project,*args,check=True): return run(['git',*args],cwd=project,capture=True,check=check)
def _read(p): return p.read_text(encoding='utf-8') if p.exists() else ''
def _agy(config,prompt,agent,effort):
    a=['agy','-p',prompt,'--agent',agent,'--output-format','text']; ac=config.get('antigravity',{})
    if ac.get('model'): a += ['--model',ac['model']]
    if effort: a += ['--effort',effort]
    if ac.get('sandbox',True): a += ['--sandbox']
    if ac.get('fullAuto',False): a += ['--dangerously-skip-permissions']
    a += ['--print-timeout',str(ac.get('printTimeout','60m'))]; return a

def _probe_cli(name,path,timeout=15):
    try: result=subprocess.run([path,'--version'],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    except (OSError,subprocess.TimeoutExpired) as exc: return False,f'{type(exc).__name__}: {exc}'
    output=(result.stdout or result.stderr).strip().splitlines(); return result.returncode==0, output[0] if output else f'exit code {result.returncode}'

def doctor(project,deep=False):
    project=project.resolve(); checks={'git':which('git'),'agy':which('agy'),'claude':which('claude'),'codex':which('codex'),'python':sys.executable}
    try: repo=ensure_git_repo(project); git_ok=True
    except Exception: repo=project; git_ok=False
    print('AI Engineering Team - doctor'+(' (deep)' if deep else '')); deep_ok=True
    for n,v in checks.items():
        req=n in {'git','agy','python'}; print(f"[{'OK' if v else ('FAIL' if req else 'WARN')}] {n}: {v or ('wymagane' if req else 'opcjonalne')}")
        if deep and v and n!='python':
            ok,detail=_probe_cli(n,v); print(f"[{'OK' if ok else ('FAIL' if req else 'WARN')}] {n} version: {detail}"); deep_ok &= ok or not req
    print(f"[{'OK' if git_ok else 'FAIL'}] git repository: {repo}"); cfg=project/'ai-team.config.json'; print(f"[{'OK' if cfg.exists() else 'FAIL'}] config: {cfg}")
    return 0 if checks['git'] and checks['agy'] and git_ok and cfg.exists() and deep_ok else 1

def _pipeline(project, prompt, manifest, rd, config):
    mp, tp = rd/'run.json', rd/'trace.jsonl'; base=manifest['base_ref']; impl=config.get('antigravity',{}).get('implementationEffort','high')
    def stage(name, cmd, out, err, allow=False):
        if manifest['stages'].get(name,{}).get('status')=='succeeded': return 0
        return _stage_capture(name,manifest,mp,tp,cmd,project,out,err,allow_failure=allow,repo_root=project)
    triage_out=rd/'triage.txt'; stage('triage',_agy(config,f'Przeprowadź triage zadania. USER TASK:\n{prompt}','triage',config.get('antigravity',{}).get('triageEffort','low')),triage_out,rd/'triage.stderr.txt')
    triage=_read(triage_out); m=re.search(r'(?im)^\s*RISK:\s*(LOW|MEDIUM|HIGH)\s*$',triage); risk=m.group(1).upper() if m else manifest.get('risk','HIGH'); manifest['risk']=risk; save_json(mp,manifest)
    stage('primary',_agy(config,f'Wykonaj zadanie. RUN DIRECTORY: {rd}\nBASE REF: {base}\nRISK: {risk}\nTRIAGE:\n{triage}\nUSER TASK:\n{prompt}','orchestrator',impl),rd/'primary.md',rd/'primary.stderr.txt')
    completed=[]
    for reviewer in config.get('reviewPolicy',{}).get(risk,[]):
        name=f'review-{reviewer}'; out=rd/f'{name}.md'; err=rd/f'{name}.stderr.txt'; available=which(reviewer)
        if not available:
            if config.get('availabilityFallback',True): _record_stage(manifest,mp,tp,name,out,'skipped',None); continue
            _record_stage(manifest,mp,tp,name,out,'failed',None); raise RuntimeError(f'{reviewer.capitalize()} wymagany przez policy.')
        prompt_r=f'Perform an independent READ-ONLY code review from base commit {base}. USER TASK: {prompt}. RISK: {risk}.'
        executable = reviewer
        cmd=([executable,'-p',prompt_r,'--agent','independent-reviewer','--permission-mode','plan','--output-format','text','--max-turns','8'] if reviewer=='claude' else [executable,'exec','--ephemeral',prompt_r])
        if stage(name,cmd,out,err,True)==0: completed.append(out)
    if completed:
        listing='\n'.join(map(str,completed)); stage('integration',_agy(config,f'Integrate confirmed findings. USER TASK: {prompt}\nBASE REF: {base}\nREVIEWS:\n{listing}','integrator',impl),rd/'integration.md',rd/'integration.stderr.txt')
    listing='\n'.join(map(str,completed)) or 'NONE'; stage('verifier',_agy(config,f'Final validation. USER TASK: {prompt}\nBASE REF: {base}\nREVIEWS: {listing}','verifier',config.get('antigravity',{}).get('verificationEffort','medium')),rd/'final-verification.md',rd/'final-verification.stderr.txt')
    ver=_read(rd/'final-verification.md'); m=re.search(r'(?im)^\s*VERDICT:\s*(PASS|PASS_WITH_NOTES|CHANGES_REQUIRED)\s*$',ver); manifest['final_verdict']=m.group(1) if m else 'UNKNOWN'; manifest['finished_at']=_now()
    dc=_git(project,'diff','--check',base,check=False); (rd/'final-diff-check.txt').write_text((dc.stdout or '')+(dc.stderr or ''),encoding='utf-8'); _eval_artifact(manifest,rd/'eval.json',dc.returncode)
    for name,e in manifest['stages'].items():
        if e.get('status')=='pending': _record_stage(manifest,mp,tp,name,rd/f'{name}.md','skipped',None)
    save_json(mp,manifest); return 0 if manifest['final_verdict'] in {'PASS','PASS_WITH_NOTES'} and dc.returncode==0 else 2

def run_team(project,user_prompt):
    if not which('git'): raise RuntimeError('Nie znaleziono git.')
    if not which('agy'): raise RuntimeError('Nie znaleziono agy.')
    project=ensure_git_repo(project.resolve()); cfgp=project/'ai-team.config.json'
    if not cfgp.exists(): raise RuntimeError('Brak ai-team.config.json. Najpierw ai-team install.')
    config=load_json(cfgp); status=_git(project,'status','--porcelain').stdout.strip()
    if config.get('requireCleanWorkingTree',True) and status: raise RuntimeError('Working tree nie jest czysty. Commit/stash własne zmiany.')
    current=_git(project,'branch','--show-current').stdout.strip()
    if not current: raise RuntimeError('Detached HEAD.')
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); slug=safe_slug(user_prompt); run_id=f'{stamp}-{slug}'; rd=project/'.ai/runs'/run_id; rd.mkdir(parents=True,exist_ok=True)
    (rd/'prompt.txt').write_text(user_prompt+'\n',encoding='utf-8'); (project/'.ai').mkdir(exist_ok=True); (project/'.ai/latest.txt').write_text(run_id+'\n',encoding='utf-8')
    prefix=config.get('branchPrefix','ai/')
    if config.get('createBranchForEachRun',True) and not current.startswith(prefix): branch=f'{prefix}{stamp}-{slug}'; run(['git','switch','-c',branch],cwd=project)
    else: branch=current
    base=_git(project,'rev-parse','HEAD').stdout.strip(); (rd/'base-ref.txt').write_text(base+'\n',encoding='utf-8'); (rd/'branch.txt').write_text(branch+'\n',encoding='utf-8')
    manifest={'run_id':run_id,'base_ref':base,'branch':branch,'prompt_sha256':hashlib.sha256(user_prompt.encode()).hexdigest(),'stages':{n:{'status':'pending'} for n in ('triage','primary','review','integration','verifier')},'final_verdict':None,'created_at':_now()}; save_json(rd/'run.json',manifest); (rd/'trace.jsonl').write_text('',encoding='utf-8')
    return _pipeline(project,user_prompt,manifest,rd,config)
