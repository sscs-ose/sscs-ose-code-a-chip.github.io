"""Record public development checks outside the agent's writable filesystem."""
from __future__ import annotations

import json
import os
import signal
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from study_protocol import digest, write_json

CASE = Path(__file__).resolve().parents[1]
CLIENT = '''from pathlib import Path
import json,socket,sys
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
    connection.connect('/run/study-check.sock')
    connection.sendall(b'{"check":"smoke"}\\n')
    connection.shutdown(socket.SHUT_WR)
    chunks=[]
    while True:
        data=connection.recv(65536)
        if not data:break
        chunks.append(data)
reply=json.loads(b''.join(chunks))
print(reply['output'],end='')
print('Trusted check receipt:',reply['check_id'])
sys.exit(reply['exit_code'])
'''


def rtl_hashes(workspace):
    files = sorted(workspace.glob('rtl/**/*.sv')) + sorted(workspace.glob('rtl/**/*.v'))
    files += sorted(workspace.glob('ip/**/*.sv')) + sorted(workspace.glob('ip/**/*.v'))
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(workspace.resolve()):
            raise ValueError('RTL path escapes trial workspace')
    return {str(path.relative_to(workspace)): digest(path) for path in files}


class DevelopmentChecks:
    def __init__(self, workspace, ledger, attempt):
        self.workspace, self.ledger = Path(workspace), Path(ledger)
        self.attempt = attempt
        self.directory = tempfile.TemporaryDirectory(prefix='chip-study-check-')
        self.socket = Path(self.directory.name) / 'socket'
        self.process = None
        owner = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                try:
                    request = json.loads(self.rfile.readline(1024))
                    if request != {'check': 'smoke'}:
                        raise ValueError('Only the frozen public smoke operation is exposed')
                    reply = owner.execute()
                except Exception as error:
                    reply = {'check_id': None, 'exit_code': 2, 'output': type(error).__name__ + ': ' + str(error) + '\n'}
                try: self.wfile.write(json.dumps(reply).encode())
                except BrokenPipeError: pass

        self.server = socketserver.UnixStreamServer(str(self.socket), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        if self.process is not None and self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
        self.server.shutdown(); self.thread.join(); self.server.server_close()
        self.directory.cleanup()

    def execute(self):
        self.ledger.mkdir(parents=True, exist_ok=True)
        index = len(list(self.ledger.glob('check-*.json'))) + 1
        start = time.monotonic(); hashes = rtl_hashes(self.workspace)
        out = self.workspace / 'build/public-check'; out.mkdir(parents=True, exist_ok=True)
        bench = CASE / 'generation_seed/tb/npu_smoke_tb.sv'
        commands = [['iverilog', '-g2012', '-s', 'npu_smoke_tb', '-o', str(out / 'sim'),
                     *[str(self.workspace / path) for path in hashes], str(bench)],
                    ['vvp', str(out / 'sim')]]
        output = ''; code = 1
        for command in commands:
            guarded = [sys.executable, str(CASE/'scripts/check_process_guard.py'), '--owner', str(os.getpid()), '--', *command]
            self.process = subprocess.Popen(guarded, cwd=self.workspace, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, text=True, start_new_session=True)
            try:
                text, _ = self.process.communicate(timeout=90)
                code = self.process.returncode
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                text, _ = self.process.communicate(); code = 124
            output += text
            if code: break
        stable = hashes == rtl_hashes(self.workspace)
        passed = code == 0 and 'NPU_SMOKE_PASS' in output and stable
        record = {'check_id': index, 'attempt': self.attempt, 'source_sha256': hashes,
                  'checker_sha256': digest(bench), 'source_stable': stable, 'passed': passed,
                  'exit_code': 0 if passed else code or 1, 'elapsed_seconds': time.monotonic() - start,
                  'output': output, 'commands': commands}
        write_json(self.ledger / f'check-{index:04d}.json', record)
        (out / 'smoke.log').write_text(output)
        return {key: record[key] for key in ('check_id', 'exit_code', 'output')}
