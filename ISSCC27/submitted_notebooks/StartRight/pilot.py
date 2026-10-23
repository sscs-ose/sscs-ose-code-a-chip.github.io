from pathlib import Path
import hashlib, json, subprocess, os, shutil
ROOT=Path(__file__).resolve().parent.parent.parent.parent
HERE=Path(__file__).resolve().parent
CONFIG=json.loads((HERE/'.startright_tools.json').read_text()) if (HERE/'.startright_tools.json').exists() else {}
PDK=Path(os.environ.get('STARTRIGHT_PDK') or CONFIG.get('pdk_root') or str(ROOT/'tools'/'sky130_fd_pr'))
EXE=Path(os.environ.get('STARTRIGHT_NGSPICE') or CONFIG.get('ngspice_executable') or shutil.which('ngspice') or str(ROOT/'tools'/'ngspice'/'Spice64'/'bin'/'ngspice_con.exe'))
OUT=HERE/'results'/'pilot'
OUT.mkdir(parents=True,exist_ok=True)
def models(corner='tt'):
    files=[PDK/'models'/'parameters'/'lod.spice']
    for name in ['nfet_01v8','pfet_01v8']:
        folder=PDK/'cells'/name
        files += [folder/f'sky130_fd_pr__{name}__{corner}.corner.spice',folder/f'sky130_fd_pr__{name}__mismatch.corner.spice']
    text='.option scale=1u\n.param sky130_fd_pr__nfet_01v8__dlc_rotweak=0 sky130_fd_pr__pfet_01v8__dlc_rotweak=0\n'
    return text+'\n'.join(f'.include "{p.as_posix()}"' for p in files)+'\n'
def simulate(name,deck,*,compatibility="hs",solver=None,threads=None):
    folder=OUT/name
    folder.mkdir(exist_ok=True)
    assert compatibility in ['hs','hsa']
    assert solver in [None,'sparse','klu']
    init=f'set ngbehavior={compatibility}\n'
    if solver: init+=f'option {solver}\n'
    if threads is not None:
        assert isinstance(threads,int) and threads>0
        init+=f'set num_threads={threads}\n'
    (folder/'.spiceinit').write_text(init,encoding='utf8')
    (folder/'input.cir').write_text(deck,encoding='utf8')
    result=subprocess.run([str(EXE),'-b','-o','ngspice.log','input.cir'],cwd=folder,capture_output=True,text=True,timeout=90)
    (folder/'console.log').write_text(result.stdout+result.stderr,encoding='utf8')
    log=(folder/'ngspice.log').read_text(errors='replace')
    if result.returncode or 'Error' in log or 'fatal error' in log.lower():
        raise RuntimeError(f'{name}: {result.returncode}\n{log[-5000:]}')
    warnings=[line for line in log.splitlines() if line.startswith('Warning:')]
    (folder/'run_status.json').write_text(json.dumps({'compatibility':compatibility,'requested_solver':solver,'requested_threads':threads,'deck_sha256':hashlib.sha256(deck.encode()).hexdigest(),'dc_transient_fallback':'Transient op started' in log,'returncode':result.returncode,'warning_count':len(warnings),'distinct_warnings':sorted(set(warnings))},indent=2))
    return folder
