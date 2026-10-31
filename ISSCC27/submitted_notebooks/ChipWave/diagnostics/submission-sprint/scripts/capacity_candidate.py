"""Admit the designated RTL and public implementation knobs, without grader access."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import os
from pathlib import Path

from capacity_toolbox import sandbox_command, source_hashes
from capacity_process import remaining
from study_protocol import digest, write_json

ROOT = Path(__file__).resolve().parents[1]
YOSYS_MOUNT = Path('/home/asic03/project/ChipNebula/build/rtl2gds-tools/yosys-0.69+77')
ABC_MOUNT = YOSYS_MOUNT.parent/'oss-cad-suite'
YOSYS_ROOT = Path(os.environ.get('CHIPNEBULA_YOSYS_ROOT',YOSYS_MOUNT)).expanduser().resolve()
ABC_ROOT = Path(os.environ.get('CHIPNEBULA_ABC_ROOT',YOSYS_ROOT.parent/'oss-cad-suite')).expanduser().resolve()
YOSYS_IMAGE = 'localhost/chip-nebula-yosys-build:20260928'
DEFAULT_CONFIG = dict(utilization=40, density=.55, area_synthesis=False, repair_margin=20)
ALLOWED_CONFIG = dict(utilization=(30, 40, 50), density=(.55, .65),
                      area_synthesis=(False, True), repair_margin=(0, 10, 20))
# Synthesizable, side-effect-free language functions. File/process/DPI access is not a design input.
SYSTEM_FUNCTIONS = set('signed unsigned clog2 bits size left right low high increment dimensions '
                      'unpacked_dimensions countbits countones onehot onehot0 isunknown '
                      'itor rtoi bitstoreal realtobits shortrealtobits bitstoshortreal '
                      'ceil floor ln log10 exp sqrt pow'.split())
TOKENS = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\\[^\s]+|'
                    r'[A-Za-z_$][A-Za-z0-9_$]*|\s+|.', re.S)


def configuration(snapshot):
    folder = Path(snapshot)/'configuration'
    files = sorted(p for p in folder.rglob('*') if p.is_file()) if folder.exists() else []
    if any(p != folder/'implementation.json' for p in files):
        raise ValueError('Only configuration/implementation.json is configurable')
    value = json.loads(files[0].read_text()) if files else dict(DEFAULT_CONFIG)
    if not isinstance(value, dict) or set(value) != set(ALLOWED_CONFIG):
        raise ValueError('Implementation configuration must contain exactly the four public knobs')
    for key, allowed in ALLOWED_CONFIG.items():
        if type(value[key]) is not type(DEFAULT_CONFIG[key]) or value[key] not in allowed:
            raise ValueError('Illegal implementation value: '+key)
    return value


def clean_preprocessed(text):
    """Remove compiler metacomments; reject active host operations after macro expansion."""
    output, tokens = [], []
    for match in TOKENS.finditer(text):
        word = match[0]
        if word.startswith(('/*', '//')):
            output.append('\n'*word.count('\n')+' ')
            continue
        if word.startswith('"') and tokens and tokens[-1] in ('import', 'export'):
            raise ValueError('DPI is outside the synthesizable module contract')
        if word.startswith('$') and word[1:] not in SYSTEM_FUNCTIONS:
            raise ValueError('Side-effecting or unsupported system operation: '+word)
        if word in ('bind', 'config'):
            raise ValueError('Candidate cannot bind into or configure frozen neighbors')
        output.append(word)
        if not word.isspace():
            tokens.append(word)
    # Icarus emits expanded source; retained compiler directives are deliberately explicit.
    cleaned = ''.join(output)
    for line in cleaned.splitlines():
        if '`' in line and not re.fullmatch(r'\s*`(?:timescale\s+\d+\s*[munpf]?s\s*/\s*\d+\s*[munpf]?s|'
                                           r'default_nettype\s+(?:none|wire)|resetall|celldefine|endcelldefine)\s*', line):
            raise ValueError('Unexpanded or unsupported compiler directive')
    names = []
    for index, word in enumerate(tokens[:-1]):
        if word in ('module', 'macromodule'):
            at = index+1
            if tokens[at] in ('automatic', 'static'):
                at += 1
            names.append(tokens[at].lstrip('\\'))
    if len(names) != len(set(names)):
        raise ValueError('Duplicate module definitions')
    return cleaned, names


def yosys_command(directory, script):
    """Use the already pinned image with only this attempt and tool installation mounted."""
    directory = Path(directory).resolve()
    return ['podman', 'run', '--rm', '--network=none', '--security-opt', 'label=disable',
            '--security-opt', 'seccomp=unconfined',
            '--read-only', '--tmpfs', '/tmp:rw', '--env', 'HOME=/tmp',
            '--volume', f'{directory}:/work:rw',
            # Keep the pinned binary's compiled-in ABC path inside the container only.
            '--volume', f'{YOSYS_ROOT}:{YOSYS_MOUNT}:ro', '--workdir', '/work',
            '--volume', f'{ABC_ROOT}:{ABC_MOUNT}:ro',
            '--entrypoint', str(YOSYS_MOUNT/'bin/yosys'), YOSYS_IMAGE,
            '-Q', '-T', '-s', script]


def run_yosys(directory, script, timeout=120):
    """Stop the container as well as its client on a timeout."""
    directory = Path(directory)
    cid = directory/'container.id'
    command = yosys_command(directory, script)
    command[3:3] = ['--cidfile', str(cid)]
    try:
        return subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    finally:
        if cid.exists():
            identity = cid.read_text().strip()
            if re.fullmatch(r'[a-f0-9]{64}', identity):
                subprocess.run(['podman', 'rm', '-f', identity], capture_output=True, timeout=30)


def admit(snapshot, task, output, *, functional_only=False, deadline=None):
    """Expand includes with no evaluator mounted, then elaborate the fixed interface."""
    snapshot, output = Path(snapshot).resolve(), Path(output).resolve()
    if task not in ('A1', 'A2', 'B1', 'B2'):
        raise ValueError('Unknown task')
    before = source_hashes(snapshot)
    knobs = dict(DEFAULT_CONFIG) if functional_only else configuration(snapshot)
    interface = json.loads((ROOT/'tasks'/task/'agent/spec/interface.json').read_text())
    sources = sorted((snapshot/'rtl').rglob('*'))
    files = [p for p in sources if p.is_file()]
    if not files or any(p.suffix not in ('.v', '.sv', '.vh', '.svh') for p in files):
        raise ValueError('RTL must contain Verilog/SystemVerilog source and include files')
    units = [p for p in files if p.suffix in ('.v', '.sv')]
    if not units:
        raise ValueError('No RTL compilation units')
    output.mkdir(parents=True, exist_ok=False)
    stage = output/'input'
    (stage/'build').mkdir(parents=True)
    shutil.copytree(snapshot/'rtl', stage/'rtl')
    command = ['/tools/iverilog', '-g2012', '-E', '-Irtl', '-o', 'build/expanded.sv',
               *[str(p.relative_to(snapshot)) for p in units]]
    result = subprocess.run(sandbox_command(stage, command, simulation=True, writable=('build',)),
                            text=True, capture_output=True, timeout=remaining(deadline,60))
    (output/'preprocess.log').write_text(result.stdout+result.stderr)
    if result.returncode:
        raise ValueError('RTL preprocessing failed; see preprocess.log')
    normalized, modules = clean_preprocessed((stage/'build/expanded.sv').read_text())
    frozen = ROOT/'integration'/task/'rtl'
    reserved = set()
    for path in frozen.rglob('*.sv'):
        if 'candidate' not in path.parts:
            reserved.update(re.findall(r'\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)', path.read_text()))
    if reserved.intersection(modules):
        raise ValueError('Candidate redefines a frozen CPU or neighboring module')
    if interface['top'] not in modules:
        raise ValueError('Required module missing')
    (output/'design.sv').write_text(normalized)
    (output/'inspect.ys').write_text(f"read_slang -j 2 --top {interface['top']} --no-default-translate-off-format design.sv\n"
                                   f"hierarchy -check -top {interface['top']}\n"
                                   'proc\nopt_clean\ncheck -assert\nwrite_json design.json\nstat\n')
    result = run_yosys(output, 'inspect.ys',timeout=remaining(deadline,120))
    (output/'elaboration.log').write_text(result.stdout+result.stderr)
    if result.returncode:
        raise ValueError('RTL elaboration failed; see elaboration.log')
    design = json.loads((output/'design.json').read_text())
    if any(int(module.get('attributes', {}).get(flag, '0'), 2)
           for module in design['modules'].values() for flag in ('blackbox', 'whitebox')):
        raise ValueError('Unimplemented black/white-box cells are outside the task contract')
    actual = {name: (port['direction'], len(port['bits']))
              for name, port in design['modules'][interface['top']]['ports'].items()}
    expected = {p['name']: ({'in':'input', 'out':'output'}[p['direction']], p['width'])
                for p in interface['ports']}
    if actual != expected:
        raise ValueError('Elaborated ports differ from the frozen task interface')
    if source_hashes(snapshot) != before:
        raise ValueError('Submission changed during admission')
    receipt = dict(task=task, passed=True, source_sha256=before, configuration=knobs,
                   configuration_checked=not functional_only,
                   canonical_rtl_sha256=digest(output/'design.sv'), modules=modules,
                   interface_sha256=digest(ROOT/'tasks'/task/'agent/spec/interface.json'),
                   policy='Preprocessed source without metacomments is used for both function and implementation',
                   model_calls=0, physical_attempts=0)
    write_json(output/'admission.json', receipt)
    return receipt
