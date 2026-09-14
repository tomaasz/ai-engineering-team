"""Validated provider-neutral configuration; never infer shell commands."""
from pathlib import Path

from .utils import load_json, project_path

PROVIDERS = ('agy', 'codex', 'claude')
LANGUAGES = ('en', 'pl')
ROLES = ('triage', 'orchestrator', 'reviewer', 'integrator', 'verifier')
EFFORTS = ('low', 'medium', 'high')
DEFAULT_POLICY = {'LOW': ['codex'], 'MEDIUM': ['codex'], 'HIGH': ['claude', 'codex']}
BOOLEAN_KEYS = ('requireCleanWorkingTree', 'createBranchForEachRun', 'availabilityFallback',
                'reuseBranchForFollowUp', 'skipFinalVerificationAtLow', 'allowUnreviewedLowRisk',
                'useWorktree')
                'useWorktree', 'autoMerge')
# Keys the runner actually reads. Anything else is drift and must fail loudly.
ANTIGRAVITY_KEYS = {'model', 'sandbox', 'fullAuto', 'printTimeout',
                    'triageEffort', 'implementationEffort', 'verificationEffort'}
EFFORT_KEYS = ('triageEffort', 'implementationEffort', 'verificationEffort')
# Argv heads that re-introduce shell semantics the direct-exec contract exists to avoid.
SHELL_WRAPPERS = {'bash', 'sh', 'zsh', 'fish', 'dash', 'ksh', 'csh', 'tcsh',
                  'cmd', 'cmd.exe', 'powershell', 'powershell.exe', 'pwsh', 'pwsh.exe',
                  'env', 'eval', 'xargs', 'nohup', 'timeout', 'watch'}
# Ignored by Git, but still worth protecting from a stage that claims to be read-only.
DEFAULT_PROTECTED_IGNORED = ('.env', '.env.*', '*.pem', '*.key', '*.p12', '*.pfx', '*.jks')
GUARDRAIL_FILES = ('ai-team.config.json', 'AI_TEAM.md', 'PROJECT_CONTEXT.md',
                   'AGENTS.md', 'CLAUDE.md', 'GEMINI.md')


def _strings(value):
    return isinstance(value, list) and all(isinstance(x, str) and x for x in value)


def _validate_models(config):
    models = config.get('models', {})
    if not isinstance(models, dict) or any(k not in PROVIDERS for k in models):
        raise ValueError('models must map provider names to model identifiers')
    for provider, value in models.items():
        if isinstance(value, str) and value:
            continue
        if not isinstance(value, dict) or not value:
            raise ValueError(f'models.{provider} must be a model identifier or a role mapping')
        for role, identifier in value.items():
            if role != 'default' and role not in ROLES:
                raise ValueError(f'models.{provider} has unknown role {role}')
            if not isinstance(identifier, str) or not identifier:
                raise ValueError(f'models.{provider}.{role} must be a model identifier')


def _validate_provider_args(config):
    provider_args = config.get('providerArgs', {})
    if not isinstance(provider_args, dict) or any(k not in PROVIDERS for k in provider_args):
        raise ValueError('providerArgs must map provider names to role argument arrays')
    for provider, roles in provider_args.items():
        if not isinstance(roles, dict):
            raise ValueError(f'providerArgs.{provider} must be an object keyed by role')
        for role, args in roles.items():
            if role != 'default' and role not in ROLES:
                raise ValueError(f'providerArgs.{provider} has unknown role {role}')
            if not _strings(args):
                raise ValueError(f'providerArgs.{provider}.{role} must be an array of arguments')


def _validate_role_providers(config, policy):
    role_providers = config.get('roleProviders', {})
    if not isinstance(role_providers, dict) or any(k != 'integrator' for k in role_providers):
        raise ValueError('roleProviders currently supports only the integrator role')
    integrator = role_providers.get('integrator')
    if integrator is None:
        return
    if integrator not in PROVIDERS:
        raise ValueError(f'roleProviders.integrator must be one of {", ".join(PROVIDERS)}')
    for risk, reviewers in policy.items():
        if isinstance(reviewers, list) and reviewers == [integrator]:
            raise ValueError(f'roleProviders.integrator cannot be the only {risk} reviewer; '
                             'its own fix would never get an independent verdict')


def _validate_verification(config, project):
    verification = config.get('verification', {})
    if not isinstance(verification, dict) or not isinstance(verification.get('commands', []), list):
        raise ValueError('verification.commands must be an array')
    if not isinstance(verification.get('noChecksReason', ''), str):
        raise ValueError('verification.noChecksReason must be a string')
    for command in verification.get('commands', []):
        if not isinstance(command, dict):
            raise ValueError('Each verification command must be an object')
        argv = command.get('argv')
        if not _strings(argv) or not argv:
            raise ValueError('verification argv must be a nonempty array of strings')
        if 'allowShellWrapper' in command and not isinstance(command['allowShellWrapper'], bool):
            raise ValueError('verification allowShellWrapper must be boolean')
        if Path(argv[0]).name.lower() in SHELL_WRAPPERS and not command.get('allowShellWrapper'):
            raise ValueError(f'{argv[0]} re-introduces shell semantics; '
                             'set allowShellWrapper true to accept that risk explicitly')
        cwd = command.get('cwd', '.')
        if not isinstance(cwd, str) or not project_path(project, cwd).is_dir():
            raise ValueError(f'Invalid verification cwd: {cwd}')
        timeout = command.get('timeoutSeconds', 300)
        if type(timeout) is not int or timeout < 1:
            raise ValueError('verification timeoutSeconds must be positive')


def validate(config, project):
    if not isinstance(config, dict):
        raise ValueError('Configuration must be a JSON object')
    provider = config.get('primaryProvider', 'agy')
    if provider not in PROVIDERS:
        raise ValueError(f'Unsupported primaryProvider: {provider}')
    for key in BOOLEAN_KEYS:
        if key in config and not isinstance(config[key], bool):
            raise ValueError(f'{key} must be boolean')
    prefix = config.get('branchPrefix', 'ai/')
    if not isinstance(prefix, str) or not prefix.startswith('ai/') or '..' in prefix:
        raise ValueError('branchPrefix must start with ai/ and cannot contain ..')
    ac = config.get('antigravity', {})
    if not isinstance(ac, dict):
        raise ValueError('antigravity must be an object')
    unknown = set(ac) - ANTIGRAVITY_KEYS
    if unknown:
        raise ValueError('Unknown antigravity keys (the runner ignores them): ' + ', '.join(sorted(unknown)))
    for key in ('sandbox', 'fullAuto'):
        if key in ac and not isinstance(ac[key], bool):
            raise ValueError(f'antigravity.{key} must be boolean')
    for key in EFFORT_KEYS:
        if key in ac and ac[key] not in EFFORTS:
            raise ValueError(f'antigravity.{key} must be one of {", ".join(EFFORTS)} (Effort level)')
    _validate_models(config)
    _validate_provider_args(config)
    policy = config.get('reviewPolicy', DEFAULT_POLICY)
    if not isinstance(policy, dict) or set(policy) != set(DEFAULT_POLICY):
        raise ValueError('reviewPolicy must specify LOW, MEDIUM and HIGH')
    unreviewed_low = config.get('allowUnreviewedLowRisk', False)
    for risk, reviewers in policy.items():
        minimum = {'LOW': 0 if unreviewed_low else 1, 'MEDIUM': 1, 'HIGH': 2}[risk]
        if (not isinstance(reviewers, list) or any(x not in PROVIDERS or x == provider for x in reviewers)
                or len(set(reviewers)) != len(reviewers) or len(reviewers) < minimum):
            if risk == 'LOW' and isinstance(reviewers, list) and not reviewers:
                raise ValueError('LOW needs one independent reviewer; set allowUnreviewedLowRisk '
                                 'to true to accept unreviewed low-risk runs')
            raise ValueError(f'{risk} needs {minimum} distinct reviewers independent of primaryProvider')
    _validate_role_providers(config, policy)
    for key, default in [('agentTimeoutSeconds', 3600), ('runTimeoutSeconds', 14400), ('maxReviewRounds', 2)]:
        value = config.get(key, default)
        if type(value) is not int or value < 1 or (key == 'maxReviewRounds' and value > 5):
            raise ValueError(f'{key} must be positive (maxReviewRounds <= 5)')
    _validate_verification(config, project)
    risk_paths = config.get('riskPaths', {})
    if not isinstance(risk_paths, dict) or any(k not in DEFAULT_POLICY or not _strings(v)
                                               for k, v in risk_paths.items()):
        raise ValueError('riskPaths must map risk levels to glob arrays')
    passthrough = config.get('passthroughEnv', [])
    if not _strings(passthrough) or any(not x.replace('_', 'a').isalnum() or x[0].isdigit()
                                        for x in passthrough):
        raise ValueError('passthroughEnv must be an array of environment variable names')
    if not _strings(config.get('protectedIgnoredPaths', [])):
        raise ValueError('protectedIgnoredPaths must be an array of glob strings')
    if config.get('language', 'en') not in LANGUAGES:
        raise ValueError('language must be one of ' + ', '.join(LANGUAGES))
    return config


def load_config(project):
    return validate(load_json(project / 'ai-team.config.json'), project)
