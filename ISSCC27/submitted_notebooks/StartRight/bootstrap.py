"""Download pinned local dependencies. No system installation is performed."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,hashlib,json,os,shutil,subprocess,sys,urllib.request

HERE=Path(__file__).resolve().parent
MANIFEST=json.loads((HERE/'dependency_manifest.json').read_text())
CACHE=HERE/'.cache'

def download(url,path,sha256):
    path=Path(path)
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==sha256:return 'cached'
    path.parent.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(url,timeout=45) as response:data=response.read()
    if hashlib.sha256(data).hexdigest()!=sha256:raise RuntimeError(f'Checksum mismatch: {path.name}')
    temporary=path.with_name(path.name+'.partial')
    temporary.write_bytes(data);temporary.replace(path)
    return 'downloaded'

def setup():
    model_root=CACHE/'sky130_fd_pr'
    commit=MANIFEST['pdk_commit']
    def fetch(item):
        relative,info=item
        target=(model_root/relative).resolve()
        if not target.is_relative_to(model_root.resolve()):raise RuntimeError('Unsafe model path')
        url=f'https://raw.githubusercontent.com/google/skywater-pdk-libs-sky130_fd_pr/{commit}/{relative}'
        return download(url,target,info['sha256'])
    with ThreadPoolExecutor(max_workers=4) as pool:states=list(pool.map(fetch,MANIFEST['pdk_files'].items()))
    if sys.platform=='win32':
        seven=shutil.which('7z') or str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'7-Zip/7z.exe')
        if not Path(seven).exists():raise RuntimeError('Install 7-Zip or add 7z to PATH before bootstrapping on Windows.')
        archive=CACHE/'ngspice-47_64.7z'
        download(MANIFEST['ngspice_windows_url'],archive,MANIFEST['ngspice_windows_sha256'])
        exe=CACHE/'ngspice'/'Spice64'/'bin'/'ngspice_con.exe'
        if not exe.exists():
            subprocess.run([seven,'x',str(archive),'-o'+str(CACHE/'ngspice'),'-y'],check=True,capture_output=True,text=True)
    else:
        located=os.environ.get('STARTRIGHT_NGSPICE') or shutil.which('ngspice')
        if not located:raise RuntimeError('Install ngspice 47, then rerun bootstrap.py. Automatic Linux/macOS installation is not provided.')
        exe=Path(located)
    version=subprocess.check_output([str(exe),'--version'],text=True)
    if 'ngspice-47 ' not in version:raise RuntimeError('This reproduction requires ngspice 47.')
    config={'pdk_root':str(model_root.resolve()),'ngspice_executable':str(exe.resolve())}
    (HERE/'.startright_tools.json').write_text(json.dumps(config,indent=2))
    report={'model_commit':commit,'verified_model_files':len(states),'downloaded_model_files':states.count('downloaded'),'ngspice_version':version,'config':config,'manifest_sha256':hashlib.sha256((HERE/'dependency_manifest.json').read_bytes()).hexdigest()}
    (HERE/'bootstrap_report.json').write_text(json.dumps(report,indent=2))
    print('Verified',len(states),'model/license files and ngspice 47.')
    return report

if __name__=='__main__':setup()
