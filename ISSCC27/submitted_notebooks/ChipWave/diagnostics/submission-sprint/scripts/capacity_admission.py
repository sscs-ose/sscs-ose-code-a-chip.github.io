"""Fail-closed admission of preregistered trials against the qualified frozen campaign."""
import json
import shutil
import subprocess
import hashlib
import os
import tomllib
from pathlib import Path

from capacity_integration_physical import ROOT
from capacity_protocol import MODELS
from study_protocol import digest


def service_fingerprint():
    path=Path.home()/'.codex/config.toml'
    settings=tomllib.loads(path.read_text()) if path.exists() else {}
    keys=('model_provider','model_providers','chatgpt_base_url','cli_auth_credentials_store','force_login_method')
    transport={key:settings[key] for key in keys if key in settings}
    transport['environment']={key:os.environ[key] for key in
        ('OPENAI_BASE_URL','OPENAI_ORG_ID','OPENAI_PROJECT_ID') if key in os.environ}
    # Only a digest leaves the owner; provider configuration can contain credentials.
    return hashlib.sha256(json.dumps(transport,sort_keys=True).encode()).hexdigest()


def runtime_paths():
    from capacity_candidate import YOSYS_ROOT,ABC_ROOT,YOSYS_IMAGE
    from capacity_integration_physical import CASE
    return dict(case=str(CASE.resolve()),yosys=str(YOSYS_ROOT),abc=str(ABC_ROOT),yosys_image=YOSYS_IMAGE)


def admit_trial(category, identity):
    if category not in ('pilot','formal'):
        raise ValueError('A scored invocation needs an explicit trial category')
    frozen=ROOT/'campaign-freeze.json'
    if not frozen.is_file():raise ValueError('Reference/task/runtime qualification has not been frozen')
    freeze=json.loads(frozen.read_text())
    if freeze.get('qualified') is not True:raise ValueError('Campaign prerequisites are not qualified')
    if freeze.get('schema_version')!=2:raise ValueError('Unsupported campaign qualification schema')
    if freeze['service_fingerprint']!=service_fingerprint():raise ValueError('Model service configuration changed')
    if freeze['runtime_paths']!=runtime_paths():raise ValueError('Frozen public component/tool roots changed')
    native=os.environ.get('CHIP_STUDY_CODEX_BINARY') or shutil.which('codex-real') or str(Path.home()/'.codex/packages/standalone/current/bin/codex')
    if str(Path(native).resolve())!=freeze['native_binary']:raise ValueError('Native Codex binary selection changed')
    for name,sha in freeze['files'].items():
        path=ROOT/name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or digest(path)!=sha:
            raise ValueError('Frozen campaign input changed: '+name)
    for name,sha in freeze['external_files'].items():
        if digest(Path(name))!=sha:raise ValueError('Frozen tool/runtime source changed: '+name)
    for name,path in freeze['tool_paths'].items():
        found=shutil.which(name)
        if not found or str(Path(found).resolve())!=path:
            raise ValueError('Frozen tool resolution changed: '+name)
    for name,image_identity in freeze['container_images'].items():
        actual=subprocess.check_output(['podman','image','inspect','--format','{{.Id}}',name],text=True,timeout=30).strip()
        if actual!=image_identity:raise ValueError('Frozen tool image changed: '+name)
    from import_capacity_prior import validate_inherited
    validate_inherited(ROOT)
    protocol=json.loads((ROOT/'protocol.json').read_text())
    if protocol.get(category+'_launch_allowed') is not True:
        raise ValueError('Trial category has not passed its launch gate')
    jobs=protocol['pilot_jobs' if category=='pilot' else 'formal_jobs']
    matching=[row for row in jobs if row['id']==identity]
    if len(matching)!=1:raise ValueError('Trial is not uniquely preregistered')
    job=matching[0]
    if job['model'] not in MODELS.values():raise ValueError('Unapproved trial model')
    invariant={k:protocol[k] for k in freeze['protocol']}
    if invariant!=freeze['protocol']:raise ValueError('Frozen resource/task protocol changed')
    if category=='formal':
        decision=json.loads((ROOT/'pilot-decision.json').read_text())
        if decision.get('campaign_sha256')!=digest(frozen):raise ValueError('Pilot decision belongs to another campaign')
        if decision.get('formal_launch_allowed') is not True or decision.get('stop_rule_triggered') is not False:
            raise ValueError('Pilot discrimination/validity gate did not admit formal trials')
        for name,sha in decision['pilot_evidence'].items():
            if digest(ROOT/name)!=sha:raise ValueError('Pilot evidence changed after the launch decision')
    return dict(job)


def validate_runtime(config):
    eda=config.get('eda',{})
    job=admit_trial(eda.get('category'),eda.get('trial'))
    if eda.get('task')!=job['task'] or config.get('model')!=job['model']:
        raise ValueError('Runtime model/task differs from the preregistered trial')
    trial=ROOT/'trials'/eda['category']/job['id']
    if (Path(config['record']).resolve()!=trial/'runtime' or Path(config['project']).resolve()!=trial/'project'
            or not Path(config['workspace']).resolve().is_relative_to(trial/'project')):
        raise ValueError('Trial cannot reset its accounting or switch project')
    if config.get('limit',1_000_000)!=1_000_000 or config.get('active_seconds',5400)!=5400 or config.get('preflight_compact_at') is not None:
        raise ValueError('Scored budgets/configuration differ from the frozen study')
    if (trial/'result.json').exists():raise ValueError('Terminal trial cannot be restarted')
    return job
