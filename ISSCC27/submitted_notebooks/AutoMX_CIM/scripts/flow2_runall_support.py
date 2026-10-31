"""Notebook execution helpers: bounded native logs, verified cache, views.

Large outputs live in a user-selected persistent work directory; the source
checkout and historical signoff receipts are never used as scratch storage.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
import codecs
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import time


def digest(path):
    with Path(path).open('rb') as f:
        import hashlib
        return hashlib.file_digest(f,'sha256').hexdigest()


def item(path):
    p=Path(path).resolve();return {'path':str(p),'sha256':digest(p)}


def verified(value):
    path=Path(value['path'])
    if not path.is_file() or digest(path)!=value['sha256']:raise ValueError('artifact hash differs: '+str(path))
    return path


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');temporary.replace(path)


@dataclass(frozen=True)
class Settings:
    root:Path
    cache:Path=Path('/media/nam/EDABK/AutoMX_CIM_runall_20261023')
    tag:str='runall_srv_20261023_01'
    reuse:bool=True
    timeout_s:int=180
    jobs:int=3


class Flow:
    def __init__(self,settings):
        from scripts.flow2_integration_common import tag_ok
        tag_ok(settings.tag)
        if not 1<=settings.jobs<=8 or settings.timeout_s<=0:raise ValueError('bounded tools/concurrency required')
        self.settings=settings;self.root=Path(settings.root).resolve()
        self.base=Path(settings.cache).expanduser().resolve();self.work=self.base/settings.tag
        self.work.mkdir(parents=True,exist_ok=True)
        self.receipts={};self.outputs={}
        if shutil.disk_usage(self.base).free<1024**3:raise ValueError('work directory needs at least 1 GiB free')
        print('Python:',os.sys.executable,'\nSource:',self.root,'\nWork:',self.work,flush=True)

    def log(self,path,head=14,tail=35):
        path=Path(path);lines=path.read_text(errors='replace').splitlines()
        print('\nNative log:',path,flush=True)
        selected=lines if len(lines)<=head+tail else [*lines[:head],f'... {len(lines)-head-tail} lines retained in log ...',*lines[-tail:]]
        print('\n'.join(selected),flush=True)

    def run(self,name,command,*,inputs=(),outputs=(),env=None,timeout_s=None,cwd=None):
        from scripts.flow2_integration_common import tag_ok
        tag_ok(name);work=Path(cwd) if cwd else self.work/name;work.mkdir(parents=True,exist_ok=True)
        command=list(map(str,command));identity={'command':command,'sources':[item(p) for p in inputs],
            'environment':env or {},'timeout_s':timeout_s or self.settings.timeout_s}
        files=[Path(p) if Path(p).is_absolute() else work/p for p in outputs]
        receipt=work/(name+'.step.json') if cwd else work/'step.json'
        native=work/(name+'.native.log') if cwd else work/'native.log'
        if self.settings.reuse and receipt.is_file():
            prior=json.loads(receipt.read_text())
            if prior['identity']==identity and prior.get('returncode')==0 and {str(p) for p in files}=={v['path'] for v in prior['outputs']}:
                try:
                    for v in prior['outputs']:verified(v)
                    verified(prior['log'])
                except (ValueError,OSError):pass
                else:
                    print('REUSE (hash verified):',name,flush=True);self.log(native)
                    self.receipts[name]=item(receipt);return prior
        # Preserve any previous run before writing a replacement attempt.
        if native.exists():
            prior_dir=work/('prior_'+name+'_'+str(time.time_ns()));prior_dir.mkdir()
            shutil.copy2(native,prior_dir/native.name)
            if receipt.exists():
                shutil.copy2(receipt,prior_dir/receipt.name)
                prior=json.loads(receipt.read_text())
                for index,artifact in enumerate(prior.get('outputs',[])):
                    old=Path(artifact['path'])
                    if old.is_file():shutil.copy2(old,prior_dir/(str(index)+'_'+old.name))
        # Keep small executed source files, indexed by content, for review.
        snapshots=work/'executed_sources';snapshots.mkdir(exist_ok=True)
        for source in identity['sources']:
            path=Path(source['path'])
            if path.suffix in ('.py','.v','.sv','.tcl','.ys','.json') and path.stat().st_size<2*1024**2:
                snapshot=snapshots/(source['sha256']+'_'+path.name)
                if not snapshot.exists():shutil.copy2(path,snapshot)
        print('RUN',name,':',' '.join(command),flush=True)
        actual=[*command];environment=os.environ.copy();environment.update(env or {})
        if actual[0]!='docker' and shutil.which('stdbuf'):actual=['stdbuf','-oL','-eL',*actual]
        start=time.monotonic();last=start;decoder=codecs.getincrementaldecoder('utf-8')('replace')
        process=subprocess.Popen(actual,cwd=work,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                 start_new_session=True)
        selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
        code=None
        try:
            with native.open('wb') as stream:
                while True:
                    now=time.monotonic()
                    if now-start>identity['timeout_s']:
                        os.killpg(process.pid,signal.SIGTERM)
                        try:process.wait(timeout=3)
                        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL)
                        code=124;stream.write(b'\nBOUNDED_TOOL_TIMEOUT\n');print('\nBOUNDED_TOOL_TIMEOUT',flush=True);break
                    events=selector.select(.25)
                    for key,_ in events:
                        data=os.read(key.fd,65536)
                        if not data:selector.unregister(key.fileobj);continue
                        stream.write(data);stream.flush()
                        print(decoder.decode(data),end='',flush=True)
                    if now-last>=30:print(name,':',round(now-start),'s; full log',native,flush=True);last=now
                    if process.poll() is not None and not selector.get_map():code=process.returncode;break
        finally:
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            selector.close()
            if command[0]=='docker' and '--name' in command:
                container=command[command.index('--name')+1]
                subprocess.run(['docker','rm','-f',container],capture_output=True,timeout=15)
        print(decoder.decode(b'',final=True),end='',flush=True)
        for source in identity['sources']:verified(source)
        report={'identity':identity,'returncode':code,'elapsed_s':time.monotonic()-start,
                'outputs':[item(p) for p in files if p.is_file()],'log':item(native)}
        save(receipt,report);self.receipts[name]=item(receipt)
        print('\nEXIT',name,':',code,'| elapsed_s:',round(report['elapsed_s'],3),'| log:',native,flush=True)
        if code or any(not p.is_file() for p in files):raise RuntimeError(name+' incomplete; inspect '+str(native))
        return report

    def container(self,program,args,name,work=None):
        from scripts.run_flow2_wrapper_postroute import container_command
        command=container_command(self.root,program,args,'automx-'+self.settings.tag+'-'+name)
        command[2:2]=['-v',str(self.base)+':'+str(self.base)]
        command[command.index('-w')+1]=str(work or self.work)
        return command

    def render(self,gds,top,name):
        from IPython.display import Image,display
        gds=Path(gds);work=self.work/('render_'+name);png=work/(name+'.png')
        script=self.root/'scripts/render_flow2_wrapper_gds.py'
        self.run('render_'+name,['klayout','-z','-x','-r',script],inputs=[gds,script],outputs=[png],
            env={'QT_QPA_PLATFORM':'offscreen','AUTOMX_GDS':str(gds),'AUTOMX_PNG':str(png),'AUTOMX_TOP':top})
        if png.read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('invalid rendered PNG')
        display(Image(filename=str(png)));self.outputs[name+'_png']=item(png)
        return png
