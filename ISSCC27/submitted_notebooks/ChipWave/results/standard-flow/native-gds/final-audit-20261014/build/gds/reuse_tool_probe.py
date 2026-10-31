import hashlib
import json
import os
from pathlib import Path
import pya

out=Path(__file__).resolve().parent
prior=json.loads((out/'klayout_runtime_identity.json').read_text())
version=pya.Application.instance().version()
exe=Path(os.readlink('/proc/self/exe'))
h=hashlib.sha256(exe.read_bytes()).hexdigest()
assert version==prior['raw_application_version'] and h==prior['actual_executable_sha256']
(out/'current_klayout_identity.json').write_text(json.dumps(dict(status='passed',version=version,
    executable=str(exe),sha256=h,prior_evidence='build/gds/klayout_runtime_identity.json',
    scope='Read-only executable identity qualification for reuse; no GDS or deck check rerun.'),indent=2)+'\n')
print('REUSE_KLAYOUT_BINARY_IDENTITY_PASS')
