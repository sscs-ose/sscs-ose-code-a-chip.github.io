import hashlib, json, re, subprocess, os
from pathlib import Path

OUT = Path('reports/synthesis')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(name, data): (OUT / name).write_text(json.dumps(data, indent=2) + '\n')

records = []
for aid in ['artifact-478b595695d0419e81e4d77e864a23d7', 'artifact-e8950ffbafd54dd0b6512b9cf536b9c2', 'artifact-2f225eabd33249d79dbc17a7b73ec146', 'artifact-210d9f6d592a4c08ae346ffd8e1d074a']:
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
assert c['status'] == 'frozen'
assert c['memory']['memory_macros'] == c['memory']['required_views'] == []
assert not c['memory']['external_memories']['inside_physical_top']
assert c['memory']['architectural_register_file']['implementation'] == 'verified standard-cell flops and muxes'
assert sha('physical/chip-nebula/constraints.sdc') == c['sdc_sha256']
views = []
for name, v in c['view_binding']['views'].items():
    p = Path(v['installed_path'])
    assert sha(p) == v['sha256'] == lock['platform']['views'][name]['sha256'], name
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
write('liberty_cells.json', cells)
tool_hashes = []
for name in ['/tmp/chipnebula-pinned-tools/bin/yosys', '/tmp/chipnebula-pinned-tools/bin/eda-container-run', '/home/asic03/project/ChipNebula/build/rtl2gds-tools/yosys-0.69+77/bin/yosys', '/home/asic03/project/ChipNebula/build/rtl2gds-tools/oss-cad-suite/bin/yosys-abc', '/eda/opensource/openroad/26Q3/bin/sta']:
    tool_hashes.append(dict(path=name, sha256=sha(name), bytes=Path(name).stat().st_size))
write('tool_identity.json', dict(tools=tool_hashes, yosys_version=version, sta_version=subprocess.check_output(['/eda/opensource/openroad/26Q3/bin/sta', '-version'],text=True).strip(), note='The pinned opensta alias resolves to OpenROAD and needs a technology DB; actual standalone OpenSTA is invoked directly for Liberty-only pre-layout STA.'))
write('input_audit.json', dict(verdict='passed', records=records, views=views, orfs_revision_observed=rev, orfs_revision_declared=c['view_binding']['orfs_revision'], orfs_revision_note='Installed platform is an exported directory without Git metadata; revision comes from frozen constraints and lock, not an independent Git measurement.', yosys=version, verification_verdict='passed', units=dict(time='ns', capacitance='pF', liberty_area='um2', lef_length='um'), captured_manifest_available=Path(c['view_binding']['manifest_path']).exists(), note='Captured manifest is absent from this attempt; exact frozen view_binding plus integration lock validates all 20 installed resources. No views substituted.'))
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
