import csv
import hashlib
import json
from pathlib import Path
import pya

root = Path(__file__).resolve().parents[2]
c = json.loads((root / 'physical/chip-nebula/implementation.constraints.json').read_text())
gds = Path(c['view_binding']['views']['gds/sky130_fd_sc_hd.gds']['installed_path'])
assert hashlib.sha256(gds.read_bytes()).hexdigest() == c['view_binding']['views']['gds/sky130_fd_sc_hd.gds']['sha256'], 'Error-Class: invalid_physical_view: frozen GDS changed'
raw_version = pya.Application.instance().version()
version = raw_version.removeprefix('KLayout ')
print('KLAYOUT_APPLICATION_VERSION', raw_version)
assert version == '0.30.12', 'KLayout actual stream-out version differs'
layout = pya.Layout()
layout.read(str(gds))
available = {cell.name for cell in layout.each_cell()}
with (root / 'reports/pnr/database_instances.tsv').open() as f:
    used = {row['master'] for row in csv.DictReader(f, delimiter='\t')}
missing = sorted(used - available)
report = dict(schema_version=1, status='passed' if not missing else 'failed',
              library_gds=str(gds), klayout_version=version, raw_application_version=raw_version, gds_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(),
              used_masters=sorted(used), missing_masters=missing,
              note='Checks only masters actually instantiated in final ODB. Unused optional LEF masters do not block stream-out.')
(root / 'reports/pnr/gds_master_audit.json').write_text(json.dumps(report, indent=2) + '\n')
assert not missing, 'Error-Class: invalid_physical_view: GDS masters missing: ' + str(missing)
print('ACTUAL_ODB_GDS_MASTERS_PASS', len(used))
