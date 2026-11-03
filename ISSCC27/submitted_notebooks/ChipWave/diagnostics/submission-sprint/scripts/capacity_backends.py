"""Host-controlled synthesis and physical callbacks for the common native tool router."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

from capacity_budget import reserve, finish
from capacity_candidate import admit, run_yosys
from capacity_toolbox import source_hashes
from capacity_process import remaining
from capacity_integration_physical import ROOT, CASE, prepare, verified_integration
from study_protocol import digest, write_json


class Backends:
    def __init__(self, record, task, *, trial=None, category=None, feedback=None):
        self.record, self.task = Path(record), task
        self.trial, self.category = trial, category
        self.feedback = Path(feedback) if feedback is not None else None
        verified_integration(task)
        self.record.mkdir(parents=True, exist_ok=True)

    def handlers(self, deadline=None):
        return dict(development=lambda source,identity:self.integration(source,identity,deadline=deadline() if deadline else None),
                    synthesis_sta=lambda source,identity:self.synthesis(source,identity,deadline=deadline() if deadline else None),
                    physical=self.physical)

    def integration(self, snapshot, identity, *, deadline=None):
        from build_capacity_dot_integration import qualify
        output=self.record/f'development-{identity:04d}';output.mkdir()
        row=dict(status='infrastructure_error',task=self.task,physical_attempts=0)
        start=time.monotonic()
        try:
            admitted=admit(snapshot,self.task,output/'admitted',functional_only=True,deadline=deadline)
            source,_=verified_integration(self.task)
            project=output/'integration';project.mkdir()
            for name in ('rtl','verification','workloads'):
                shutil.copytree(source/name,project/name)
            shutil.rmtree(project/'rtl/candidate');(project/'rtl/candidate').mkdir()
            shutil.copy2(output/'admitted/design.sv',project/'rtl/candidate/design.sv')
            checked=qualify(project,seeds=(17,),deadline=deadline)
            row.update(status='passed' if checked['passed'] else 'failed',checks=checked['rows'],
                       source_sha256=admitted['source_sha256'],canonical_rtl_sha256=admitted['canonical_rtl_sha256'],
                       scope='Public CPU workload integration at development memory seed17; no hidden final checker')
        except ValueError as error:
            row.update(status='failed',error=str(error))
        except subprocess.TimeoutExpired as error:
            row.update(status='timeout',error=str(error))
        except Exception as error:
            row.update(error=str(error));(output/'error.log').write_text(traceback.format_exc())
        row['seconds']=time.monotonic()-start
        write_json(output/'result.json',row)
        return self.result(output,row)

    def synthesis(self, snapshot, identity, *, functional_only=False, deadline=None):
        output = self.record/f'synthesis-{identity:04d}'
        output.mkdir()
        start = time.monotonic()
        row = dict(status='infrastructure_error', task=self.task, physical_attempts=0)
        try:
            admitted = admit(snapshot, self.task, output/'admitted',functional_only=functional_only,deadline=deadline)
            source, _ = verified_integration(self.task)
            shutil.copytree(source/'rtl', output/'rtl')
            shutil.rmtree(output/'rtl/candidate')
            (output/'rtl/candidate').mkdir()
            shutil.copy2(output/'admitted/design.sv', output/'rtl/candidate/design.sv')
            files = ' '.join(str(p.relative_to(output)) for p in sorted((output/'rtl').rglob('*.sv')))
            (output/'synthesis.ys').write_text(
                'read_slang -j 2 --top nebula_cpu_npu_top '+files+'\n'
                'synth -top nebula_cpu_npu_top\ncheck -assert\n'
                'write_json synthesis.json\nstat\n')
            result = run_yosys(output, 'synthesis.ys', timeout=remaining(deadline,300))
            (output/'synthesis.log').write_text(result.stdout+result.stderr)
            row.update(status='passed' if result.returncode == 0 else 'failed',
                       source_sha256=admitted['source_sha256'],
                       canonical_rtl_sha256=admitted['canonical_rtl_sha256'],
                       configuration=admitted['configuration'], exit_code=result.returncode,
                       scope='Full frozen CPU integration generic synthesis; no mapped area or STA claim')
            if result.returncode == 0:
                design = json.loads((output/'synthesis.json').read_text())
                row['generic_cells_by_module'] = {name: len(module.get('cells', {}))
                                                  for name, module in design['modules'].items()}
        except ValueError as error:
            row.update(status='failed', error=str(error))
        except subprocess.TimeoutExpired as error:
            row.update(status='timeout', error=str(error))
        except Exception as error:
            row.update(error=str(error))
            (output/'error.log').write_text(traceback.format_exc())
        row['seconds'] = time.monotonic()-start
        write_json(output/'result.json', row)
        return self.result(output, row)

    def physical(self, snapshot, identity):
        # Reference preflights must use their allocated driver, never this scored-session entry.
        if self.category not in ('pilot', 'formal') or self.trial is None:
            raise ValueError('Physical execution requires a preregistered pilot/formal trial')
        name = f'{self.trial}-physical-{identity:04d}'
        output = self.record/name
        if output.exists():
            raise ValueError('Prior physical attempt is immutable')
        reserve(ROOT, self.category, self.trial, name)
        output.mkdir()
        row = dict(status='infrastructure_error', task=self.task, identity=name, qualified=False,
                   tool_id=identity,capture_id=Path(snapshot).name,source_sha256=source_hashes(snapshot))
        start = time.monotonic()
        try:
            admitted = admit(snapshot, self.task, output/'admitted',deadline=start+14400)
            os.environ.update(ORFS_ROOT=str(CASE/'toolchain/orfs'), NUM_CORES='2')
            sys.path.append(str(CASE/'scripts'))
            from run_capacity_reference import execute_physical
            manifest = prepare(output/'project', self.task, candidate=output/'admitted')
            write_json(output/'manifest.json', manifest)
            result, status = execute_physical(output, manifest, self.task,physical_deadline=start+14400)
            row.update(result, status=status, source_sha256=admitted['source_sha256'],
                       canonical_rtl_sha256=admitted['canonical_rtl_sha256'])
        except ValueError as error:
            row.update(status='failed', error=str(error))
        except subprocess.TimeoutExpired as error:
            row.update(status='timeout', error=str(error))
        except Exception as error:
            row.update(error=str(error))
            (output/'error.log').write_text(traceback.format_exc())
        row['seconds'] = time.monotonic()-start
        write_json(output/'result.json', row)
        finish(ROOT, name, row['status'], str(output/'result.json'))
        return self.result(output, row)

    def result(self, output, row):
        logs = {}
        for relative in ('admitted/preprocess.log', 'admitted/elaboration.log', 'synthesis.log'):
            path = output/relative
            if path.exists():
                logs[relative] = path.read_text()[-24000:]
        feedback = None
        if self.feedback is not None:
            # Model-writable report copies never replace protected measurement evidence.
            if any(p.is_symlink() for p in (self.feedback, *self.feedback.parents)):
                raise ValueError('Feedback path cannot traverse a symlink')
            target = self.feedback/output.name
            target.mkdir(parents=True, exist_ok=False)
            files = [output/'result.json']
            for folder in ('admitted', 'evidence', 'integration/qualification'):
                files.extend(p for p in (output/folder).rglob('*')
                             if p.is_file() and p.suffix in ('.log', '.rpt', '.json', '.txt'))
            files.extend(p for p in (output/'synthesis.log', output/'workflow.log', output/'postroute-driver.log')
                         if p.exists())
            hashes = {}
            for path in files:
                if path.is_symlink():
                    raise ValueError('Unexpected feedback symlink')
                relative = path.relative_to(output)
                (target/relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target/relative)
                hashes[str(relative)] = digest(path)
            write_json(target/'feedback-manifest.json', dict(source_sha256=row.get('source_sha256'), files=hashes))
            feedback = str(target)
        return dict(status=row['status'], evidence=str(output/'result.json'),
                    exit_code=0 if row['status'] == 'passed' else 1,
                    output=json.dumps(dict(result=row, diagnostics=logs, full_reports=feedback), indent=2))
