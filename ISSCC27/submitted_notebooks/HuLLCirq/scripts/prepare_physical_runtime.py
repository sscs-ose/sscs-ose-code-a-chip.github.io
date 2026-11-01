"""Prepare the pinned S11 AppImage, Ciel PDK, byte manifests and runtime profile.

Windows + existing WSL2 Ubuntu. Downloads/caches stay inside this project's
ignored .work directory. Existing conflicting files are preserved and rejected.
No model, project history or circuit execution is started by this script.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hullcirq.physical_tools import RELEASE,IMAGE_SHA,PDK_REVISION,SDC_SHA
from hullcirq.verification import _wsl_path,trusted_command

IMAGE_URL=f'https://github.com/librelane/librelane/releases/download/{RELEASE}/librelane-devshell-x86_64.AppImage'
SDC_URL=f'https://raw.githubusercontent.com/librelane/librelane/{RELEASE}/librelane/scripts/base.sdc'

def sha(path):
    with path.open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()

def write_exact(path,raw):
    if path.exists():
        existing=path.read_bytes()
        # Early Windows preparation used write_text and retained CRLF JSON.
        # Reuse those exact authoritative bytes and hashes; only newline
        # representation may differ from this script's new LF serialization.
        if existing!=raw and existing.replace(b'\r\n',b'\n')!=raw.replace(b'\r\n',b'\n'):
            raise RuntimeError('Conflicting existing file preserved: '+str(path))
    else:path.write_bytes(raw)

def json_bytes(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')

def download(url,path,expected,expected_size=None):
    if path.exists():
        if sha(path)!=expected or (expected_size is not None and path.stat().st_size!=expected_size):
            raise RuntimeError('Conflicting download preserved: '+str(path))
        return {'url':url,'sha256':expected,'bytes':path.stat().st_size,'action':'verified_existing'}
    partial=path.with_suffix(path.suffix+'.part')
    if partial.exists():raise RuntimeError('Partial download preserved; inspect before retry: '+str(partial))
    with urlopen(Request(url,headers={'User-Agent':'HuLLCirq-pinned-runtime-preparation'}),timeout=60) as response,partial.open('wb') as out:
        while block:=response.read(4*1024*1024):out.write(block)
    if sha(partial)!=expected or (expected_size is not None and partial.stat().st_size!=expected_size):
        raise RuntimeError('Integrity mismatch; partial download preserved: '+str(partial))
    partial.rename(path)
    return {'url':url,'sha256':expected,'bytes':path.stat().st_size,'action':'downloaded_and_verified'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'.work/physical-runtime')
    parser.add_argument('--distribution',default='Ubuntu')
    parser.add_argument('--normalize-linux-file-links',action='store_true',
                        help='Fresh setup only: validate/record internal Linux file links before Windows hashing.')
    args=parser.parse_args()
    folder=args.output.resolve()
    if not folder.is_relative_to((ROOT/'.work').resolve()):parser.error('Use a directory below HuLLCirq/.work.')
    if args.normalize_linux_file_links and ((folder/'pdk-input-manifest.json').exists() or (folder/'physical_runtime.json').exists()):
        raise RuntimeError('Existing PDK/profile is immutable; preserve it and use a fresh output.')
    folder.mkdir(parents=True,exist_ok=True);(folder/'runtime').mkdir(exist_ok=True)
    report={'record_kind':'pinned_environment_preparation_not_circuit_or_model_evidence','started_at':datetime.now(timezone.utc).isoformat(),'commands':[],'downloads':[]}
    image=folder/'runtime/librelane-devshell-x86_64.AppImage'
    sdc=folder/'official_base.sdc'
    print('Verifying/downloading pinned LibreLane AppImage and base SDC.',flush=True)
    report['downloads'].append(download(IMAGE_URL,image,IMAGE_SHA,1398053408))
    report['downloads'].append(download(SDC_URL,sdc,SDC_SHA))
    tool={'kind':'wsl','distribution':args.distribution}
    commands=[trusted_command(tool,'/bin/chmod',['u+x',_wsl_path(image)],ROOT),
              trusted_command(tool,_wsl_path(image),['ciel','fetch','--pdk-root',_wsl_path(folder/'pdks'),'--pdk-family','sky130','-l','default','-l','sky130_fd_sc_hd',PDK_REVISION],ROOT)]
    token=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    for index,command in enumerate(commands):
        log=folder/f'prepare-{token}-{index}.log'
        print('Preparing pinned PDK/runtime; raw output: '+str(log),flush=True)
        with log.open('wb') as out:process=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=1800,shell=False)
        report['commands'].append({'command':command,'exit_code':process.returncode,'log':str(log),'log_sha256':sha(log)})
        if process.returncode:raise RuntimeError('Environment preparation failed; inspect '+str(log))
    pdk=folder/'pdks/ciel/sky130/versions'/PDK_REVISION/'sky130A'
    if not pdk.is_dir():raise RuntimeError('Pinned PDK is missing after Ciel fetch.')
    if args.normalize_linux_file_links:
        command=['wsl.exe','-d',args.distribution,'--exec','/usr/bin/python3',
                 _wsl_path(ROOT/'scripts/fresh_linux_links.py'),'normalize',_wsl_path(pdk),
                 _wsl_path(folder/'linux-link-provenance.json'),'--allowed-root',_wsl_path(ROOT/'.work')]
        subprocess.run(command,cwd=ROOT,check=True,timeout=1200,shell=False)
    print('Hashing installed PDK files; preserving full input provenance.',flush=True)
    if args.normalize_linux_file_links:
        from fresh_runtime import inventory
        files=inventory(pdk)
    else:
        files={p.relative_to(pdk).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(pdk.rglob('*')) if p.is_file()}
    manifest=folder/'pdk-input-manifest.json'
    write_exact(manifest,json_bytes({'pdk':'sky130A','ciel_revision':PDK_REVISION,'root':str(pdk),'origin':'Ciel_2.4.0_pinned_LibreLane_3.0.16_fetch','files':files}))
    config={'kind':'wsl','distribution':args.distribution,'origin':'development_assistant_execution_profile_under_user_authorization_original_GUI_settings_unchanged',
            'release':RELEASE,'appimage_path':str(image),'executable':_wsl_path(image),'appimage_sha256':IMAGE_SHA,'pdk_revision':PDK_REVISION,'pdk_root':str(folder/'pdks'),
            'pdk_manifest_path':str(manifest),'pdk_manifest_sha256':sha(manifest),'base_sdc_path':str(sdc),'base_sdc_sha256':SDC_SHA,
            'working_directory':str(folder/'layout'),'profile':json.loads((ROOT/'configs/physical_profile_sky130.json').read_text(encoding='utf-8'))}
    output=folder/'physical_runtime.json'
    write_exact(output,json_bytes(config))
    report.update(validation_status='Passed',runtime_configuration=str(output),runtime_configuration_sha256=sha(output),PDK_files=len(files),PDK_bytes=sum(v['bytes'] for v in files.values()),pdk_manifest_sha256=sha(manifest),actual_tool_starts=0,model_calls=0,project_history_writes=0)
    (folder/f'prepare-{token}-report.json').write_bytes(json_bytes(report))
    print(json.dumps({k:v for k,v in report.items() if k not in ('commands','downloads')},indent=2),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
