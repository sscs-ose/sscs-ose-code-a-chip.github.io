import hashlib
import json
import os
from pathlib import Path
import pya

version=pya.Application.instance().version()
assert version.removeprefix('KLayout ')=='0.30.12'
executable=Path(os.readlink('/proc/self/exe'))
h=hashlib.sha256(executable.read_bytes()).hexdigest()
result=dict(status='passed',raw_application_version=version,actual_executable=str(executable),actual_executable_sha256=h,
            pya_module=pya.__file__,context='Measured inside the actual KLayout execution environment, using the same pinned wrapper as stream-out and decks.')
Path(__file__).resolve().with_name('klayout_runtime_identity.json').write_text(json.dumps(result,indent=2)+'\n')
print('KLAYOUT_ACTUAL_RUNTIME_IDENTITY_PASS',version,str(executable),h)
