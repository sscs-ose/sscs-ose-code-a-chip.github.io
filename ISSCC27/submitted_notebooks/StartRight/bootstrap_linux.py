"""Build pinned ngspice 47 locally on Linux, then configure the model bootstrap.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import argparse, hashlib, json, os, platform, shutil, subprocess, sys, tarfile
from bootstrap import download,HERE,MANIFEST,CACHE,setup


def build(jobs=2,source_archive=None):
    if sys.platform!='linux':raise RuntimeError('This source-build helper is for Linux.')
    if not 1<=jobs<=16:raise ValueError('Use between 1 and 16 build jobs.')
    for program in ['gcc','g++','make']:
        if not shutil.which(program):raise RuntimeError(f'Missing {program}. Install a C/C++ build toolchain before running this helper.')
    pinned=MANIFEST['ngspice_source'];archive=CACHE/'ngspice-47.tar.gz'
    if source_archive:
        supplied=Path(source_archive)
        if hashlib.sha256(supplied.read_bytes()).hexdigest()!=pinned['sha256']:raise RuntimeError('Source archive checksum mismatch.')
        archive.parent.mkdir(parents=True,exist_ok=True)
        if supplied.resolve()!=archive.resolve():shutil.copyfile(supplied,archive)
    else:download(pinned['url'],archive,pinned['sha256'])
    source=CACHE/'ngspice-source';source.mkdir(parents=True,exist_ok=True)
    prefix=(CACHE/'ngspice-linux').resolve();executable=prefix/'bin/ngspice'
    options=['--prefix='+str(prefix),'--without-x','--with-readline=no','--with-fftw3=no','--enable-klu','--enable-openmp','--disable-debug']
    stamp=prefix/'startright_build.json'
    if not executable.exists() or not stamp.exists():
        with tarfile.open(archive) as package:package.extractall(source,filter='data')
        working=source/'ngspice-47'
        env=os.environ.copy();env['CFLAGS']='-O2';env['CXXFLAGS']='-O2'
        for name,command in [('configure',['./configure',*options]),('make',['make',f'-j{jobs}']),('install',['make','install'])]:
            print('Building ngspice:',name,flush=True)
            with (CACHE/f'linux_{name}.log').open('w',encoding='utf8') as log:
                result=subprocess.run(command,cwd=working,env=env,stdout=log,stderr=subprocess.STDOUT)
            if result.returncode:raise RuntimeError(f'{name} failed; inspect .cache/linux_{name}.log')
        version=subprocess.check_output([str(executable),'--version'],text=True)
        if 'ngspice-47 ' not in version:raise RuntimeError('Unexpected ngspice version after source build.')
        record={'source':pinned,'configure_options':options,'CFLAGS':env['CFLAGS'],'CXXFLAGS':env['CXXFLAGS'],'compiler':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],'platform':platform.platform(),'ngspice_version':version,'executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest()}
        stamp.write_text(json.dumps(record,indent=2),encoding='utf8')
    record=json.loads(stamp.read_text())
    if record['source']['sha256']!=pinned['sha256'] or hashlib.sha256(executable.read_bytes()).hexdigest()!=record['executable_sha256']:raise RuntimeError('Cached source-build provenance check failed.')
    os.environ['STARTRIGHT_NGSPICE']=str(executable)
    report=setup()
    report['linux_source_build']=record
    (HERE/'bootstrap_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('PASS: local source-built ngspice and pinned model setup.',flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs',type=int,default=2)
    parser.add_argument('--source-archive',type=Path,help='Optional local archive; its pinned checksum is still required')
    args=parser.parse_args();build(args.jobs,args.source_archive)

if __name__=='__main__':main()
