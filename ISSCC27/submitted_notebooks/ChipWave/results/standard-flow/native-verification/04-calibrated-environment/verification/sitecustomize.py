"""Preserve fixed-run evidence and reuse byte-identical Verilator builds.

Loaded only by run_regression.sh. No oracle, corpus or DUT bytes are changed.
"""
import hashlib
import json
import os
import re
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time

if os.environ.get('NEBULA_VERIFY_CAPTURE'):
    ROOT = Path(os.environ['NEBULA_VERIFY_CAPTURE'])
    ROOT.mkdir(parents=True, exist_ok=True)
    original_run = subprocess.run

    class KeptDirectory:
        def __init__(self, suffix=None, prefix=None, dir=None, **kwargs):
            self.name = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=ROOT/'work')

        def __enter__(self):
            return self.name

        def __exit__(self, *args):
            pass

    (ROOT/'work').mkdir(exist_ok=True)
    tempfile.TemporaryDirectory = KeptDirectory

    def captured_run(args, *positional, **kwargs):
        command = list(map(str, args)) if isinstance(args, (list, tuple)) else args
        if not isinstance(command, list):
            return original_run(args, *positional, **kwargs)
        tag = f'{time.time_ns()}-{os.getpid()}'
        receipt = {'command': shlex.join(command), 'cwd': str(kwargs.get('cwd', Path.cwd())),
                   'pid': os.getpid(), 'ppid': os.getppid(), 'start_ns': time.time_ns(),
                   'configuration': os.environ.get('NEBULA_VERIFY_CONFIG', 'base')}
        is_compile = Path(command[0]).name == 'verilator' and '--binary' in command
        if is_compile:
            config = os.environ.get('NEBULA_VERIFY_CONFIG', 'base')
            # Transparent binding: only the public fixture's instance parameter changes.
            if config == 'enabled':
                for i, value in enumerate(command):
                    p = Path(value)
                    if p.suffix != '.sv' or '/rtl/' in value or not p.is_file():
                        continue
                    content = p.read_text()
                    if 'Compatibility entry point' in content:
                        included = re.search(r'`include "([^"]+)"', content)
                        assert included, p
                        p = p.parents[2]/included.group(1)
                        content = p.read_text()
                    old = 'rv32i_five_stage_cpu dut (.*);'
                    if old in content:
                        assert content.count(old) == 1
                        bound = ROOT/'bindings'/f'{hashlib.sha256(content.encode()).hexdigest()}.sv'
                        bound.parent.mkdir(exist_ok=True)
                        bound.write_text(content.replace(old, 'rv32i_five_stage_cpu #(.ENABLE_XNEBULA(1)) dut (.*);'))
                        command[i] = str(bound)
                        receipt['binding'] = {'original': str(p), 'bound': str(bound),
                                              'replacement': 'instance ENABLE_XNEBULA=1 only'}
            mi = command.index('--Mdir') + 1
            mdir = Path(command[mi]).resolve()
            if mdir.is_dir() and not any(mdir.iterdir()):
                mdir.rmdir()
            if command[command.index('--top-module')+1] == 'tb_cpu_elf':
                command.append(str(Path(__file__).resolve().parents[1]/'tb/architectural_observer.sv'))
            normalized = command[:mi] + ['<build>'] + command[mi+1:]
            source_hashes = {v: hashlib.sha256(Path(v).read_bytes()).hexdigest()
                             for v in command if Path(v).suffix in {'.sv', '.v'} and Path(v).is_file()}
            key = hashlib.sha256(json.dumps([normalized, source_hashes], sort_keys=True).encode()).hexdigest()
            cached = ROOT/'cache'/key
            cached.parent.mkdir(exist_ok=True)
            receipt['build_key'] = key
            if (cached/'complete.json').is_file():
                mdir.parent.mkdir(parents=True, exist_ok=True)
                assert not mdir.exists(), mdir
                mdir.symlink_to(cached/'obj', target_is_directory=True)
                receipt.update(cache_hit=True, returncode=0, end_ns=time.time_ns())
                (ROOT/f'{tag}.json').write_text(json.dumps(receipt, indent=2)+'\n')
                return subprocess.CompletedProcess(command, 0, 'Reused identical build '+key+'\n', '')
            cached.mkdir(exist_ok=True)
            command[mi] = str(cached/'obj')
            libs = ROOT/'tool-libs'
            libs.mkdir(exist_ok=True)
            link = libs/'libatomic.so'
            if not link.exists():
                link.symlink_to('/usr/lib64/libatomic.so.1')
            command += ['--coverage', '-LDFLAGS', '-L'+str(libs)]
        is_sim = Path(command[0]).name.startswith('V') or Path(command[0]).name == 'vvp'
        if is_sim:
            for argument in command:
                if argument.startswith('+IMAGE='):
                    source = Path(argument.split('=', 1)[1])
                    saved = ROOT/f'{tag}.image.hex'
                    shutil.copyfile(source, saved)
                    receipt['image'] = str(saved)
        if is_sim and Path(command[0]).name != 'vvp':
            command += [f'+verilator+coverage+file+{ROOT}/{tag}.coverage.dat']
        receipt['executed_command'] = shlex.join(command)
        try:
            result = original_run(command, *positional, **kwargs)
            receipt['returncode'] = result.returncode
            for stream in ('stdout', 'stderr'):
                value = getattr(result, stream)
                if value:
                    log = ROOT/f'{tag}.{stream}.log'
                    log.write_bytes(value.encode() if isinstance(value, str) else value)
                    receipt[stream] = str(log)
            if is_compile and result.returncode == 0:
                mdir.parent.mkdir(parents=True, exist_ok=True)
                mdir.symlink_to(cached/'obj', target_is_directory=True)
                (cached/'complete.json').write_text(json.dumps(receipt)+'\n')
            if is_sim:
                for argument in command:
                    if argument.startswith('+TRACE='):
                        source = Path(argument.split('=', 1)[1])
                        if source.exists():
                            saved = ROOT/f'{tag}.trace.jsonl'
                            shutil.copyfile(source, saved)
                            receipt['trace'] = str(saved)
                            for phase in ['initial', 'final']:
                                dump = Path(str(source)+f'.{phase}.hex')
                                if dump.exists():
                                    dst = ROOT/f'{tag}.{phase}.hex'
                                    shutil.copyfile(dump, dst)
                                    receipt[phase+'_memory'] = str(dst)
            return result
        except subprocess.TimeoutExpired as exc:
            receipt.update(returncode=None, status='timeout', timeout=exc.timeout)
            raise
        finally:
            receipt['end_ns'] = time.time_ns()
            (ROOT/f'{tag}.json').write_text(json.dumps(receipt, indent=2)+'\n')

    subprocess.run = captured_run
