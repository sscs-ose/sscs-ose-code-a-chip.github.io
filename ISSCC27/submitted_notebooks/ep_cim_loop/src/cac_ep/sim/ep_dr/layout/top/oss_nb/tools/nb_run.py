"""Helpers used by every cell of ep_cim_loop.ipynb: run a shell command, time a notebook step, keep a time table.

The notebook stays readable because the bookkeeping lives here:

    run = StepRunner(work=WORK, mode=MODE, train=TRAIN)
    with run.step('download MNIST', 'train'):
        run.sh('bash get_mnist.sh ...')

Every step is written to WORK/times.json right away, so the time table (last cell) also works after a crash.
A failing step does not stop the notebook: the error is printed, recorded, and the next cell can still run.
"""
import contextlib
import json
import os
import subprocess
import time
import traceback
from pathlib import Path

# Readable names for the step groups in the time table
GROUP_NAMES = {
    'setup': 'install',
    'train': 'training',
    'sim': 'simulation',
    'layout': 'layout',
    'route': 'routing',
    'verify': 'verification',
}

# Some tools print short Korean messages (counts, notes); the notebook shows them in English (same meaning, longest phrase first)
KO_EN = [('(정보) OBS 창: met3 128 곳', '(info) OBS windows: met3, 128 places'), ('(정보)', '(info)'), ('OBS 창', 'OBS windows'), ('대조: 모두 같음', 'check: all the same'), ('넓은 금속 둘레', 'edges of wide metal'), ('special 도형도 있는 넷', 'nets that also have special shapes'), ('도형도 있는 넷', 'nets that also have shapes'), ('패드 없는 core 핀', 'core pins without a pad'), ('core 핀 없는 패드', 'pads without a core pin'), ('lib/ subckt 겹침', 'lib/ subckt name clashes'), ('내용 다른 중복', 'duplicates with different content'), ('뺀 중복', 'duplicates removed'), ('안 쓰는 핀', 'unused pins'), ('VSS 묶음', 'tied to VSS'), ('핀 하나 넷', 'one-pin nets'), ('출력 둘 이상', 'nets with two or more drivers'), ('구동 없음', 'undriven nets'), ('대소문자 겹침', 'case clashes'), ('인스턴스', 'instances'), ('설정 쓰기', 'setting writes'), ('Python 예측', 'Python prediction'), ('예측', 'prediction'), ('core ↔ 안쪽 ring 틈', 'gap core ↔ inner ring'), ('안쪽', 'inner'), ('틈', 'gap'), ('비교기 줄', 'comparator row'), ('칸 줄', 'cell rows'), ('단락: 없음', 'shorts: none'), ('신호 핀', 'signal pins'), ('구조', 'structures'), ('행마다', 'per row'), ('시간 칸', 'time slots'), ('표본', 'samples'), ('도형', 'shapes'), (' 줄,', ' lines,'), (' 번,', ' times,'), (' 넷 ', ' nets '), ('넷', 'nets'), ('핀', 'pins'), ('줄', 'lines'), ('번', 'times'), ('곳', 'places'), ('창', 'windows'), ('겹침', 'clashes'), ('묶음', 'ties')]


def en(s):
    for a, b in KO_EN:
        s = s.replace(a, b)
    return s


class StepRunner:
    def __init__(self, work, mode, train):
        self.work = Path(work)
        self.mode = mode
        self.train = train
        (self.work / 'logs').mkdir(parents=True, exist_ok=True)
        # Time records of earlier runs in the same WORK folder are kept (the table filters by mode and start time)
        self.times_file = self.work / 'times.json'
        self.times = json.loads(self.times_file.read_text()) if self.times_file.exists() else []

    def _save(self, record):
        self.times.append(record)
        self.times_file.write_text(json.dumps(self.times, indent=1, ensure_ascii=False))

    def sh(self, cmd, log=None, tail=15, cwd=None, env=None, timeout=None):
        """Run one bash command.

        - The full output goes to a log file (WORK/logs/...); only the last `tail` lines are printed.
        - A non-zero exit code raises RuntimeError, which the surrounding `step` records as a failure.
        - Returns the output as a list of lines (for checks in the notebook).
        """
        log = Path(log) if log else self.work / 'logs' / f'sh_{int(time.time() * 1000)}.log'
        full_env = dict(os.environ, **(env or {}))
        t0 = time.time()
        with open(log, 'w') as f:
            rc = subprocess.call(['bash', '-c', cmd], stdout=f, stderr=subprocess.STDOUT,
                                 cwd=cwd, env=full_env, timeout=timeout)
        lines = log.read_text(errors='ignore').splitlines()
        for line in (lines[-tail:] if tail else []):
            print('   ', en(line)[:220])
        short = cmd[:140] + ('…' if len(cmd) > 140 else '')
        print(f'  [{time.time() - t0:.1f} s, rc={rc}] {short}')
        if rc:
            raise RuntimeError(f'rc={rc}: {cmd[:200]} (log {log})')
        return lines

    @contextlib.contextmanager
    def step(self, name, group, note=''):
        """Time one notebook step and record whether it worked.

        Use as `with run.step(...) as r:`; the cell may put a short result into r['note'] (shown in the time table).
        Exceptions inside the block are caught here, printed and recorded; the notebook goes on.
        """
        record = dict(name=name, group=group, mode=self.mode, train=self.train, note=note, start=time.time())
        print(f'■ {name} ({GROUP_NAMES.get(group, group)}) start')
        try:
            yield record
            record['ok'] = record.get('ok', True)
        except Exception as ex:
            record['ok'] = False
            record['error'] = str(ex)[:400]
            print(f'  ✗ failed: {ex}')
            traceback.print_exc(limit=1)
        record['sec'] = round(time.time() - record['start'], 1)
        self._save(record)
        status = 'ok' if record['ok'] else ('skipped' if record['ok'] is None else 'FAILED')
        print(f'■ {name}: {record["sec"]} s, {status}')

    def skip(self, name, group, why):
        """A step this mode does not run: keep the reason in the time table (0 s, 'skipped')."""
        record = dict(name=name, group=group, mode=self.mode, sec=0.0, ok=None, note=why, start=time.time())
        self._save(record)
        print(f'■ {name}: skipped — {why}')
