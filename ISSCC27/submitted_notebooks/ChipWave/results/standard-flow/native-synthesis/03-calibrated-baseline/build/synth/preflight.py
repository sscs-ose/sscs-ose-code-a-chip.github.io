import hashlib, json, re, subprocess, os
from pathlib import Path

OUT = Path('reports/synthesis')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(name, data): (OUT / name).write_text(json.dumps(data, indent=2) + '\n')

records = []
for aid in ['artifact-8bfa326445194758816c2d0d07307a6f', 'artifact-0040978541934ec0803b607ff5200dae', 'artifact-71a2cc812ae94e199187060007730850', 'artifact-7295759bd83c446780157c3cdc2d72ae']:
    path = Path('.nebula_inputs') / aid / 'artifact.json'
    a = json.loads(path.read_text())
    if a['type'] == 'verification.report': assert a['payload']['verdict'] == 'passed'
    files = []
    for name in a['content']['paths']:
        frozen = subprocess.check_output(['git', 'show', a['content']['commit'] + ':' + name])
        actual = os.readlink(name).encode() if Path(name).is_symlink() else Path(name).read_bytes()
        assert actual == frozen, name
        files.append(dict(path=name, sha256=sha(name)))
    records.append(dict(artifact_id=aid, record_sha256=sha(path), input_commit=a['content']['commit'], files=files))
assert json.loads(Path('reports/verification/report.json').read_text())['report']['verdict'] == 'passed'
c = json.loads(Path('physical/chip-nebula/implementation.constraints.json').read_text())
lock = json.loads(Path('integration/dependencies.lock.json').read_text())
assert c['status'] == 'frozen' and c['revision'] == 2
assert sha('physical/chip-nebula/implementation.constraints.json') == lock['platform']['constraints_sha256']
assert c['spec_digest'] == lock['platform']['spec_digest']
assert sha('physical/chip-nebula/constraints.sdc') == lock['platform']['sdc_sha256']
assert c['memory']['memory_macros'] == c['memory']['required_views'] == []
assert not c['memory']['external_memories']['inside_physical_top']
assert c['memory']['architectural_register_file']['implementation'] == 'verified standard-cell flops and muxes'
assert sha('physical/chip-nebula/constraints.sdc') == c['sdc_sha256']
acceptance = json.loads(Path('.nebula_inputs/artifact-8bfa326445194758816c2d0d07307a6f/artifact.json').read_text())['payload']
assert acceptance['plan']['status'] == 'frozen' and acceptance['plan']['confirmed'] is True
assert acceptance['spec_digest'] == c['spec_digest']
verification = json.loads(Path('.nebula_inputs/artifact-7295759bd83c446780157c3cdc2d72ae/artifact.json').read_text())['payload']
assert verification['spec_digest'] == c['spec_digest']
old_constraints = json.loads(Path('.nebula_inputs/artifact-e8950ffbafd54dd0b6512b9cf536b9c2/artifact.json').read_text())
old_commit = old_constraints['content']['commit']
previous_constraints = json.loads(subprocess.check_output(['git', 'show', old_commit + ':physical/chip-nebula/implementation.constraints.json']))
protected = ['synthesis', 'clocks', 'io', 'reset', 'memory', 'electrical', 'view_binding', 'platform', 'power', 'rc', 'physical_top', 'ports', 'spec_digest']
for key in protected: assert c.get(key) == previous_constraints.get(key), key
old_sdc = subprocess.check_output(['git', 'show', old_commit + ':physical/chip-nebula/constraints.sdc']).decode()
new_sdc = Path('physical/chip-nebula/constraints.sdc').read_text()
def sdc_commands(text): return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')]
assert sdc_commands(old_sdc) == sdc_commands(new_sdc)
old_integration = json.loads(Path('.nebula_inputs/artifact-2f225eabd33249d79dbc17a7b73ec146/artifact.json').read_text())
source_checks = []
for source in Path('integration/design.f').read_text().splitlines():
    previous = subprocess.check_output(['git', 'show', old_integration['content']['commit'] + ':' + source])
    assert Path(source).read_bytes() == previous, source
    source_checks.append(dict(path=source, sha256=sha(source), unchanged=True))
write('baseline_revalidation.json', dict(verdict='passed', constraints_revision=2, acceptance_revision=2, spec_digest=c['spec_digest'], current_inputs=records, prior_constraints_commit=old_commit, protected_fields_unchanged=protected, changed_constraint_fields=sorted(key for key in set(c) | set(previous_constraints) if c.get(key) != previous_constraints.get(key)), sdc_commands_identical=True, sdc_comments_changed=old_sdc != new_sdc, rtl_checks=source_checks, historical_evidence='Original published synthesis files retained byte-for-byte under build/synth/history/v1 and reports/synthesis/history/v1.', execution='Rerun mapped synthesis and standalone Liberty-only OpenSTA with current frozen SDC. V2 OpenROAD/2-core policy applies to revised physical phases; synthesis invokes no OpenROAD or PnR.', physical_qualification='Not run; historical V1 PnR remains failed and is not qualified by this synthesis result.'))
manifest_path = Path(c['view_binding']['manifest_path'])
assert sha(manifest_path) == c['view_binding']['manifest_sha256']
manifest = json.loads(manifest_path.read_text())
assert manifest['platform'] == c['platform'] and manifest['corner'] == c['corner']
assert manifest['time_unit_ns'] == manifest['capacitance_unit_pf'] == 1
views = []
for name, v in c['view_binding']['views'].items():
    p = Path(v['installed_path'])
    assert sha(p) == v['sha256'] == lock['platform']['views'][name]['sha256'] == manifest['views'][name]['sha256'], name
    assert p.stat().st_size == lock['platform']['views'][name]['size']
    views.append(dict(name=name, path=str(p), sha256=sha(p), bytes=p.stat().st_size))
assert len(views) == 20
revision_check = subprocess.run(['git', '-C', c['platform_lock']['flow_home'], 'rev-parse', 'HEAD'], text=True, capture_output=True)
rev = revision_check.stdout.strip() if revision_check.returncode == 0 else None
if rev is not None: assert rev == c['view_binding']['orfs_revision'], rev
assert lock['platform']['orfs_revision'] == c['view_binding']['orfs_revision']
sources = Path('integration/design.f').read_text().splitlines()
assert sources == [p['rtl_path'] for p in lock['packages']]
for p in lock['packages']: assert 'sha256:' + sha(p['rtl_path']) == p['content_digest']
yosys = '/tmp/chipnebula-pinned-tools/bin/yosys'
version = subprocess.check_output([yosys, '-V'], text=True).strip()
assert '0.69+77' in version and '9ff27d29c' in version
lib = c['view_binding']['views'][c['view_binding']['liberty']]['installed_path']
text = Path(lib).read_text()
assert 'time_unit : "1ns"' in text and 'capacitive_load_unit(1.0000000000, "pf")' in text
cells = {}
parts = re.split(r'\bcell\s*\("([^"\n]+)"\)\s*\{', text)
for name, body in zip(parts[1::2], parts[2::2]):
    area = re.search(r'\barea\s*:\s*([0-9.]+)', body)
    cells[name] = dict(area=float(area.group(1)), sequential=bool(re.search(r'\b(ff|latch)\s*\(', body)), latch=bool(re.search(r'\blatch\s*\(', body)))
assert len(cells) == 428, len(cells)
assert set(cells) == set(manifest['liberty_cells'])
write('liberty_cells.json', cells)
tool_hashes = []
for name in ['/tmp/chipnebula-pinned-tools/bin/yosys', '/tmp/chipnebula-pinned-tools/bin/eda-container-run', '/home/asic03/project/ChipNebula/build/rtl2gds-tools/yosys-0.69+77/bin/yosys', '/home/asic03/project/ChipNebula/build/rtl2gds-tools/oss-cad-suite/bin/yosys-abc', '/eda/opensource/openroad/26Q3/bin/sta']:
    tool_hashes.append(dict(path=name, sha256=sha(name), bytes=Path(name).stat().st_size))
write('tool_identity.json', dict(tools=tool_hashes, yosys_version=version, sta_version=subprocess.check_output(['/eda/opensource/openroad/26Q3/bin/sta', '-version'],text=True).strip(), note='The pinned opensta alias resolves to OpenROAD and needs a technology DB; actual standalone OpenSTA is invoked directly for Liberty-only pre-layout STA.'))
write('input_audit.json', dict(verdict='passed', records=records, views=views, orfs_revision_observed=rev, orfs_revision_declared=c['view_binding']['orfs_revision'], orfs_revision_note='Installed platform is an exported directory without Git metadata; revision comes from frozen constraints and lock, not an independent Git measurement.', yosys=version, verification_verdict='passed', units=dict(time='ns', capacitance='pF', liberty_area='um2', lef_length='um'), captured_manifest_available=True, captured_manifest_sha256=sha(manifest_path), note='Captured manifest digest, all 20 installed resource digests, units and complete 428-cell Liberty roster match frozen view_binding and integration lock. No views substituted.'))
dont = ' '.join('-dont_use ' + cell for cell in c['electrical']['dont_use_cells'])
Path('build/synth/abc.constr').write_text('set_driving_cell sky130_fd_sc_hd__buf_1\nset_load 5\n')
script = f"""read_slang --top nebula_cpu_npu_top -f integration/design.f --diag-json reports/synthesis/slang_diagnostics.json
hierarchy -check -top nebula_cpu_npu_top
write_json build/synth/elaborated.json
synth -top nebula_cpu_npu_top -flatten -noabc -latches error
write_json build/synth/generic.json
dfflibmap -liberty {lib} {dont}
abc -liberty {lib} {dont} -constr build/synth/abc.constr -D 100000 -script +strash;ifraig;scorr;dc2;strash;dch,-f;map,-a;buffer;upsize,-D,100000;dnsize,-D,100000;stime,-p
clean
hilomap -hicell sky130_fd_sc_hd__conb_1 HI -locell sky130_fd_sc_hd__conb_1 LO
clean
read_liberty -lib {lib}
check -assert
tee -o reports/synthesis/stat.json stat -json -liberty {lib}
write_json build/synth/mapped.json
write_verilog -noattr -noexpr -nodec build/synth/nebula_cpu_npu_top.v
"""
Path('build/synth/synth.ys').write_text(script)
print('PREFLIGHT_PASS frozen inputs, verification, 20 views, locked ORFS declaration, tool version and units')
