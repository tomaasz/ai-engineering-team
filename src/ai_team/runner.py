from pathlib import Path
from datetime import datetime
import re, subprocess, sys
from .utils import run, which, load_json, ensure_git_repo, safe_slug

def _capture(cmd,cwd,out,err,allow_failure=False):
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',encoding='utf-8') as fo, err.open('w',encoding='utf-8') as fe:
        p=subprocess.run(cmd,cwd=str(cwd),text=True,stdout=fo,stderr=fe)
    if p.returncode and not allow_failure: raise RuntimeError(f"Polecenie zakończone kodem {p.returncode}: {' '.join(cmd)}. Log: {err}")
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

def doctor(project):
    project=project.resolve(); checks={'git':which('git'),'agy':which('agy'),'claude':which('claude'),'codex':which('codex'),'python':sys.executable}
    try: repo=ensure_git_repo(project); git_ok=True
    except Exception: repo=project; git_ok=False
    print('AI Engineering Team - doctor')
    for n,v in checks.items():
        req=n in {'git','agy','python'}
        print(f"[{'OK' if v else ('FAIL' if req else 'WARN')}] {n}: {v or ('wymagane' if req else 'opcjonalne')}")
    print(f"[{'OK' if git_ok else 'FAIL'}] git repository: {repo}")
    cfg=project/'ai-team.config.json'; print(f"[{'OK' if cfg.exists() else 'FAIL'}] config: {cfg}")
    return 0 if checks['git'] and checks['agy'] and git_ok and cfg.exists() else 1

def run_team(project,user_prompt):
    if not which('git'): raise RuntimeError('Nie znaleziono git.')
    if not which('agy'): raise RuntimeError('Nie znaleziono agy.')
    project=ensure_git_repo(project.resolve()); cfgp=project/'ai-team.config.json'
    if not cfgp.exists(): raise RuntimeError('Brak ai-team.config.json. Najpierw ai-team install.')
    config=load_json(cfgp)
    status=_git(project,'status','--porcelain').stdout.strip()
    if config.get('requireCleanWorkingTree',True) and status: raise RuntimeError('Working tree nie jest czysty. Commit/stash własne zmiany.')
    current=_git(project,'branch','--show-current').stdout.strip()
    if not current: raise RuntimeError('Detached HEAD.')
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); slug=safe_slug(user_prompt); run_id=f'{stamp}-{slug}'
    rd=project/'.ai/runs'/run_id; rd.mkdir(parents=True,exist_ok=True); (rd/'prompt.txt').write_text(user_prompt+'\n',encoding='utf-8'); (project/'.ai/latest.txt').write_text(run_id+'\n',encoding='utf-8')
    prefix=config.get('branchPrefix','ai/')
    if config.get('createBranchForEachRun',True) and not current.startswith(prefix):
        branch=f'{prefix}{stamp}-{slug}'; print('==> branch:',branch); run(['git','switch','-c',branch],cwd=project)
    else: branch=current
    base=_git(project,'rev-parse','HEAD').stdout.strip(); (rd/'base-ref.txt').write_text(base+'\n',encoding='utf-8'); (rd/'branch.txt').write_text(branch+'\n',encoding='utf-8')
    print('==> Triage')
    tp=f'''Przeprowadź triage poniższego zadania w aktualnym repozytorium. Nie zmieniaj plików.\n\nUSER TASK:\n{user_prompt}\n'''
    to,te=rd/'triage.txt',rd/'triage.stderr.txt'; _capture(_agy(config,tp,'triage',config.get('antigravity',{}).get('triageEffort','low')),project,to,te)
    triage=_read(to); m=re.search(r'(?im)^\s*RISK:\s*(LOW|MEDIUM|HIGH)\s*$',triage); risk=m.group(1).upper() if m else 'HIGH'; print(triage.strip()); print('==> risk:',risk)
    print('==> Gemini/Antigravity team')
    pp=f'''Wykonaj zadanie jako główny AI Engineering Team.\n\nRUN DIRECTORY:\n{rd}\n\nBASE REF:\n{base}\n\nRISK:\n{risk}\n\nTRIAGE:\n{triage}\n\nUSER TASK:\n{user_prompt}\n\nNie wykonuj push, merge ani deployment. Zewnętrzny review Claude/Codex uruchamia dispatcher.\n'''
    impl=config.get('antigravity',{}).get('implementationEffort','high'); _capture(_agy(config,pp,'orchestrator',impl),project,rd/'primary.md',rd/'primary.stderr.txt')
    (rd/'status-after-primary.txt').write_text(_git(project,'status','--short').stdout,encoding='utf-8'); (rd/'diff-stat-after-primary.txt').write_text(_git(project,'diff','--stat',base).stdout,encoding='utf-8')
    completed=[]
    for reviewer in config.get('reviewPolicy',{}).get(risk,[]):
        if reviewer=='claude':
            if not which('claude'):
                if config.get('availabilityFallback',True): print('[WARN] Claude CLI niedostępny — pomijam.'); continue
                raise RuntimeError('Claude wymagany przez policy.')
            print('==> Claude independent review')
            rp=f'''Wykonaj niezależny, read-only code review zmian od {base} do aktualnego working tree.\nUSER TASK:\n{user_prompt}\nRISK: {risk}\nNie modyfikuj plików. Nie czytaj review innych modeli przed własną analizą. Stosuj AI_TEAM.md.\n'''
            out,err=rd/'review-claude.md',rd/'review-claude.stderr.txt'; rc=_capture(['claude','-p',rp,'--agent','independent-reviewer','--permission-mode','plan','--output-format','text','--max-turns','8'],project,out,err,True)
            if rc==0: completed.append(out)
        elif reviewer=='codex':
            if not which('codex'):
                if config.get('availabilityFallback',True): print('[WARN] Codex CLI niedostępny — pomijam.'); continue
                raise RuntimeError('Codex wymagany przez policy.')
            print('==> Codex independent review')
            rp=f'''Perform an independent READ-ONLY code review from base commit {base} to current working tree.\nUSER TASK:\n{user_prompt}\nRISK: {risk}\nFollow AGENTS.md and AI_TEAM.md. Do not modify files. Do not read other model reviews first. Prioritize correctness, regressions, security, data loss and verification.\n'''
            out,err=rd/'review-codex.md',rd/'review-codex.stderr.txt'; rc=_capture(['codex','exec','--ephemeral',rp],project,out,err,True)
            if rc==0: completed.append(out)
    if completed:
        print('==> Integrating external reviews'); listing='\n'.join(f'- {x}' for x in completed)
        ip=f'''Jesteś integratorem końcowym.\nUSER TASK:\n{user_prompt}\nRISK: {risk}\nBASE REF: {base}\nNiezależne review:\n{listing}\nSprawdź każdy finding samodzielnie. Potwierdzone napraw minimalnie, fałszywe alarmy odrzuć dowodem. Po ostatniej poprawce uruchom testy. Bez push/merge/deploy.\n'''
        _capture(_agy(config,ip,'integrator',impl),project,rd/'integration.md',rd/'integration.stderr.txt')
    print('==> Final verification'); listing='\n'.join(f'- {x}' for x in completed) if completed else 'NONE'
    vp=f'''Wykonaj końcową walidację.\nUSER TASK:\n{user_prompt}\nRISK: {risk}\nBASE REF: {base}\nREVIEW FILES:\n{listing}\nNie modyfikuj kodu. Sprawdź finalny diff, wymaganie i uruchom adekwatne testy.\n'''
    vo,ve=rd/'final-verification.md',rd/'final-verification.stderr.txt'; _capture(_agy(config,vp,'verifier',config.get('antigravity',{}).get('verificationEffort','medium')),project,vo,ve)
    ver=_read(vo); m=re.search(r'(?im)^\s*VERDICT:\s*(PASS|PASS_WITH_NOTES|CHANGES_REQUIRED)\s*$',ver); verdict=m.group(1) if m else 'UNKNOWN'
    (rd/'final-status.txt').write_text(_git(project,'status','--short').stdout,encoding='utf-8'); (rd/'final-diff-stat.txt').write_text(_git(project,'diff','--stat',base).stdout,encoding='utf-8')
    dc=_git(project,'diff','--check',base,check=False); (rd/'final-diff-check.txt').write_text((dc.stdout or '')+(dc.stderr or ''),encoding='utf-8')
    print('\n==> Gotowe'); print('Run:',run_id); print('Branch:',branch); print('Risk:',risk); print('Verdict:',verdict); print('Raporty:',rd); print('\n'+ver.strip())
    return 0 if verdict in {'PASS','PASS_WITH_NOTES'} else 2
