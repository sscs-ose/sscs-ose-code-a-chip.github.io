import sys,os,json
from pathlib import Path
prefixes=['/home/nam/Vihn/interface_verify/fpga_export_18x18_mnist_softreset/test_folder/AutoMX-CIM', '/home/nam/dependencies/openlane_src', '/home/nam/.volare', '/home/nam/.volare_openlane_30ee138_nam']
def audit(event,args):
 if event=="open" and args and isinstance(args[0],(str,bytes,os.PathLike)):
  p=os.fsdecode(args[0])
  if any(p==r or p.startswith(r+"/") for r in prefixes):raise PermissionError("External design input blocked: "+p)
bundle=Path(__file__).resolve().parents[2]
manifest=bundle/'standalone.json'
if manifest.is_file():prefixes=list(dict.fromkeys(prefixes+json.loads(manifest.read_text()).get('forbidden_roots',[])))
sys.addaudithook(audit)
