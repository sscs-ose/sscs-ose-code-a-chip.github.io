"""Freeze qualified experiment inputs and the actually used public tool/runtime sources."""
import json
import shutil
import subprocess
import os
from pathlib import Path

import chip_nebula
from capacity_candidate import YOSYS_ROOT,ABC_ROOT,YOSYS_IMAGE
from capacity_integration_physical import ROOT,CASE,verified_integration
from capacity_protocol import TASKS,MODELS,protocol
from study_protocol import digest,write_json
from capacity_admission import service_fingerprint,runtime_paths

CHECKS=('native-compaction-probe/accounting-correction','empty-source-repair','preflight-cost-reconciliation','reference-source-reuse','inherited-attempts','revised-budget','trial-validity','pause-tree','pause-edges','zero-model-core','zero-model-isolation','public-reference-isolation','new-workspace','task-contracts','task-packages',
    'long-progress-v1','long-progress-faults-v1','bounded-properties-status',
    'candidate-admission','controlled-backends','backend-feedback','public-integration-backend',
    'functional-config-separation','grading-evidence','physical-attempt-diagnostics','result-analysis','accounting-replay',
    'physical-export','physical-export-boundaries','study-export','reference-replay','reference-calibration',
    'runtime-boundaries','tool-active-deadlines','tool-router','toolbox-isolation',
    'trial-orchestration','workflow-budget-stop','pilot-decision','campaign-freeze','serial-batch','portable-paths','public-recipe-compilation',
    'taskgraph-feedback','shared-source-association','response-admission','interrupted-source-prefix',
    'live-usage-recorded-probes')
LIVE=('native-router-probe-v4','live-protected-context-v2','live-taskgraph-v2',
    'live-taskgraph-c2-v1','live-taskgraph-c3-v2','native-compaction-stop-probe',
    'native-eda-admission','native-physical-wait')
MUTABLE_PROTOCOL=('phase','pilot_launch_allowed','formal_launch_allowed','frozen_for_formal')
PRESENTATION_ONLY={'capacity_notebook_cells.py','build_capacity_manuscript.py',
                   'build_notebook.py','build_benchmark_notebook.py',
                   'render_notebook.py','package_submission.py'}


def external_sources():
    files=set()
    sdk=Path(chip_nebula.__file__).parent
    for directory in (sdk,CASE/'scripts',CASE/'toolchain/orfs'):
        files.update(p.resolve() for p in directory.rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and '.git' not in p.parts
                     and not (directory==CASE/'scripts' and p.name in PRESENTATION_ONLY))
    tools={}
    for name in ('iverilog','vvp','verilator','yosys','yosys-smtbmc','z3','openroad','klayout','git','make','gcc','g++','bwrap'):
        path=shutil.which(name)
        if not path:raise ValueError('Missing frozen tool: '+name)
        tools[name]=str(Path(path).resolve());files.add(Path(tools[name]))
    smt_root=Path(tools['yosys-smtbmc']).parent.parent/'share/yosys/python3'
    for name in ('smtio.py','ywio.py'):
        helper=smt_root/name
        if not helper.is_file():raise ValueError('Missing pinned SMT helper: '+str(helper))
        files.add(helper.resolve())
    files.add(CASE/'requirements-formal.lock.txt')
    files.add((YOSYS_ROOT/'bin/yosys').resolve());files.add((ABC_ROOT/'bin/yosys-abc').resolve())
    pinned=Path(tools['yosys']).parent.parent
    files.add(pinned/'bin/eda-container-run')
    for directory in (YOSYS_ROOT/'share',pinned/'verilator-5.048'):
        files.update(p.resolve() for p in directory.rglob('*') if p.is_file())
    native=Path(os.environ.get('CHIP_STUDY_CODEX_BINARY') or shutil.which('codex-real') or
                Path.home()/'.codex/packages/standalone/current/bin/codex')
    files.add(native.resolve())
    bundled=native.resolve().parent.parent/'codex-resources/bwrap'
    if bundled.is_file():files.add(bundled)
    images={name:subprocess.check_output(['podman','image','inspect','--format','{{.Id}}',name],
        text=True,timeout=30).strip() for name in (YOSYS_IMAGE,'localhost/chip-nebula-eda:20260928')}
    return dict(external_files={str(p):digest(p) for p in sorted(files)},tool_paths=tools,
                container_images=images,native_binary=str(native.resolve()))


def freeze():
    if (ROOT/'campaign-freeze.json').exists():raise ValueError('Existing campaign freeze is immutable')
    from import_capacity_prior import validate_inherited
    validate_inherited(ROOT)
    inputs=set();rules=json.loads((ROOT/'protocol.json').read_text())
    expected=json.loads(json.dumps(protocol()))
    immutable={key:expected[key] for key in expected if key not in MUTABLE_PROTOCOL}
    # An older draft omitted the explicit pilot-launch switch; other rules must match.
    if {key:rules.get(key) for key in immutable}!=immutable:
        raise ValueError('Campaign differs from the approved preregistered allocation')
    if (ROOT/'trials').exists():raise ValueError('Freeze must precede all scored trials')
    for name in CHECKS:
        path=ROOT/'checks'/(name+'.json')
        if json.loads(path.read_text()).get('passed') is not True:
            raise ValueError('Unqualified prerequisite: '+name)
        inputs.add(path)
    for name in LIVE:
        path=ROOT/'checks'/name/'result.json'
        if json.loads(path.read_text()).get('passed') is not True:
            raise ValueError('Unqualified native prerequisite: '+name)
        inputs.add(path)
    for model in MODELS.values():
        path=ROOT/'checks'/('connectivity-'+model.replace('.','-'))/'result.json'
        evidence=json.loads(path.read_text())
        if not evidence['connectivity_pass'] or evidence['observed_contexts']!=[dict(model=model,effort='high')]:
            raise ValueError('Exact model/effort was not observed: '+model)
        inputs.add(path)
    for task in TASKS:
        source,manifest=verified_integration(task)
        inputs.update(source/name for name in manifest['source_sha256'])
        inputs.update((source/'freeze-draft.json',source/'qualification/qualification.json'))
        for variant in ('pilot','formal'):
            package=ROOT/'task-packages'/variant/task
            receipt=json.loads((package/'package.json').read_text())
            if not all(receipt[key] is True for key in ('passed','calibrated','frozen')):
                raise ValueError('Task package not calibrated and frozen: '+str(package))
            for name,sha in receipt['source_sha256'].items():
                path=package/name
                if digest(path)!=sha:raise ValueError('Task changed after qualification: '+name)
                inputs.add(path)
            inputs.update((package/'package.json',package/'build.json'))
    inputs.update(p for p in (ROOT/'provenance').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    # Manuscript, publishing and figure styling code never runs in an evaluated design session.
    inputs.update(p for p in (ROOT/'scripts').glob('*.py')
                  if not p.name.startswith(('draw_','plot_')) and p.name not in PRESENTATION_ONLY)
    result=dict(schema_version=2,qualified=True,protocol=immutable,service_fingerprint=service_fingerprint(),runtime_paths=runtime_paths(),
        files={str(p.relative_to(ROOT)):digest(p) for p in sorted(inputs)},**external_sources(),
        presentation_exclusions=sorted(PRESENTATION_ONLY),
        evaluator_seconds=1800,evaluator_scope='Offline, separately timed; no feedback or model calls')
    write_json(ROOT/'campaign-freeze.json',result)
    rules.update(phase='pilots_ready',pilot_launch_allowed=True,formal_launch_allowed=False)
    write_json(ROOT/'protocol.json',rules)
    return dict(qualified=True,files=len(result['files']),external_files=len(result['external_files']),
                pilot_launch_allowed=True,formal_launch_allowed=False)


if __name__=='__main__':print(json.dumps(freeze()))
