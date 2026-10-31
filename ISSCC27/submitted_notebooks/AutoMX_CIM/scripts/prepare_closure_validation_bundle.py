"""Prepare an independent source tree with empty run/output directories."""
from pathlib import Path
import argparse,json,os,shutil

def prepare(root,destination):
    root=Path(root).resolve();destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=False)
    immutable=('pdks','tools','third_party','data')
    mutable=('automx_cim','ip','inputs','configs','rtl','scripts','licenses','physical','generated','tests','docs')
    for name in immutable:
        print('COPY_STATIC_INPUTS',name,flush=True)
        shutil.copytree(root/name,destination/name,copy_function=os.link,symlinks=True,ignore=shutil.ignore_patterns('__pycache__'))
    for name in mutable:
        if (root/name).is_dir():shutil.copytree(root/name,destination/name,symlinks=True,ignore=shutil.ignore_patterns('__pycache__'))
    for name in ['README.md','NOTICE.md','LICENSE','TEAM.json','standalone.json','relocated_configuration.json','requirements.txt','environment.yml','execute_standalone.py','run_all.sh','run_notebook.sh','spice_dependency_audit.json','AutoMX_CIM_Code_a_Chip.ipynb']:
        shutil.copy2(root/name,destination/name)
    # Break hard links for every configuration file that relocation may edit.
    for relative in json.loads((destination/'relocated_configuration.json').read_text()):
        target=destination/relative;data=target.read_bytes();target.unlink();target.write_bytes(data)
    manifest=json.loads((destination/'standalone.json').read_text())
    manifest['forbidden_roots']=list(dict.fromkeys([*manifest.get('forbidden_roots',[]),str(root)]))
    (destination/'standalone.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for name in (*immutable,*mutable):
        for path in (destination/name).rglob('*'):
            if path.is_symlink():
                target=os.readlink(path)
                if target.startswith(str(root)+'/'):
                    path.unlink();path.symlink_to(str(destination)+target[len(str(root)):])
    guard=destination/'tools/python_guard/sitecustomize.py'
    guard_text=guard.read_text();guard.unlink()
    if "manifest=bundle/'standalone.json'" not in guard_text:
        guard_text=guard_text.replace('sys.addaudithook(audit)',"bundle=Path(__file__).resolve().parents[2]\nmanifest=bundle/'standalone.json'\nif manifest.is_file():prefixes=list(dict.fromkeys(prefixes+json.loads(manifest.read_text()).get('forbidden_roots',[])))\nsys.addaudithook(audit)")
    guard.write_text(guard_text)
    (destination/'exports').mkdir();(destination/'experiments/closure_20261028').mkdir(parents=True)
    report={'status':'PREPARED','root':str(destination),'source_tree':str(root),'old_run_directories_copied':False,
       'existing_run_outputs_copied':False,'declared_reference_fixtures_included':True,'static_input_file_storage':'hard links, independent path names; source/config/code files copied',
       'original_bundle_opens_forbidden_by_python_audit':True,'candidate_views_installed':False}
    (destination/'validation_bundle.json').write_text(json.dumps(report,indent=2)+'\n');print('VALIDATION_BUNDLE_PREPARED',destination,flush=True);return destination

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--destination',type=Path,required=True);a=p.parse_args();prepare(a.root,a.destination)
