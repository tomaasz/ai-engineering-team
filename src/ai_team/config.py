"""Validated provider-neutral configuration; never infer shell commands."""
from .utils import load_json, project_path

PROVIDERS = ('agy', 'codex', 'claude')
DEFAULT_POLICY = {'LOW': [], 'MEDIUM': ['codex'], 'HIGH': ['claude', 'codex']}


def validate(config, project):
    if not isinstance(config, dict):
        raise ValueError('Configuration must be a JSON object')
    provider = config.get('primaryProvider', 'agy')
    if provider not in PROVIDERS:
        raise ValueError(f'Unsupported primaryProvider: {provider}')
    for key in ('requireCleanWorkingTree', 'createBranchForEachRun', 'availabilityFallback'):
        if key in config and not isinstance(config[key], bool):
            raise ValueError(f'{key} must be boolean')
    prefix = config.get('branchPrefix', 'ai/')
    if not isinstance(prefix, str) or not prefix.startswith('ai/') or '..' in prefix:
        raise ValueError('branchPrefix must start with ai/ and cannot contain ..')
    ac = config.get('antigravity', {})
    if not isinstance(ac, dict):
        raise ValueError('antigravity must be an object')
    for key in ('sandbox', 'fullAuto'):
        if key in ac and not isinstance(ac[key], bool):
            raise ValueError(f'antigravity.{key} must be boolean')
    models = config.get('models', {})
    if not isinstance(models, dict) or any(k not in PROVIDERS or not isinstance(v, str) for k,v in models.items()):
        raise ValueError('models must map provider names to model identifiers')
    policy = config.get('reviewPolicy', DEFAULT_POLICY)
    if not isinstance(policy, dict) or set(policy) != set(DEFAULT_POLICY):
        raise ValueError('reviewPolicy must specify LOW, MEDIUM and HIGH')
    for risk, reviewers in policy.items():
        minimum = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}[risk]
        if (not isinstance(reviewers, list) or any(x not in PROVIDERS or x == provider for x in reviewers)
                or len(set(reviewers)) != len(reviewers) or len(reviewers) < minimum):
            raise ValueError(f'{risk} needs {minimum} distinct reviewers independent of primaryProvider')
    for key, default in [('agentTimeoutSeconds', 3600), ('runTimeoutSeconds', 14400), ('maxReviewRounds', 2)]:
        value = config.get(key, default)
        if type(value) is not int or value < 1 or (key == 'maxReviewRounds' and value > 5):
            raise ValueError(f'{key} must be positive (maxReviewRounds <= 5)')
    verification = config.get('verification', {})
    if not isinstance(verification, dict) or not isinstance(verification.get('commands', []), list):
        raise ValueError('verification.commands must be an array')
    if not isinstance(verification.get('noChecksReason', ''), str):
        raise ValueError('verification.noChecksReason must be a string')
    for command in verification.get('commands', []):
        if not isinstance(command, dict):
            raise ValueError('Each verification command must be an object')
        argv = command.get('argv')
        if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x for x in argv):
            raise ValueError('verification argv must be a nonempty array of strings')
        cwd = command.get('cwd', '.')
        if not isinstance(cwd, str) or not project_path(project, cwd).is_dir():
            raise ValueError(f'Invalid verification cwd: {cwd}')
        timeout = command.get('timeoutSeconds', 300)
        if type(timeout) is not int or timeout < 1:
            raise ValueError('verification timeoutSeconds must be positive')
    risk_paths = config.get('riskPaths', {})
    if not isinstance(risk_paths, dict) or any(k not in DEFAULT_POLICY or not isinstance(v, list)
            or any(not isinstance(p, str) for p in v) for k,v in risk_paths.items()):
        raise ValueError('riskPaths must map risk levels to glob arrays')
    return config


def load_config(project):
    return validate(load_json(project / 'ai-team.config.json'), project)
