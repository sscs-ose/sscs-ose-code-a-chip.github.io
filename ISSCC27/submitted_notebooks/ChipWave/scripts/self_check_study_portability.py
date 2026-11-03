"""Probe real isolated tools, hidden answers and read-only contracts without a model."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import tomllib
from unittest.mock import patch

from study_portability import private_context,sandbox_command
from study_isolation import prepare_credentials


def credential_checks():
    with tempfile.TemporaryDirectory(prefix='chip-credential-check-') as temporary:
        root=Path(temporary);home=root/'home';account=home/'.codex';account.mkdir(parents=True)
        (account/'auth.json').write_text('{"fixture":true}')
        with patch('pathlib.Path.home',return_value=home):
            private=root/'private-no-config';prepare_credentials(private)
            assert (private/'auth.json').read_bytes()==(account/'auth.json').read_bytes()
            assert private.stat().st_mode & 0o777==0o700
            assert (private/'auth.json').stat().st_mode & 0o777==0o600
            assert tomllib.loads((private/'config.toml').read_text())=={'features':{'multi_agent':False}}
            (account/'config.toml').write_text('model_provider="fixture"\n[projects]\nprivate_project="do not copy"\n')
            private=root/'private-with-config';prepare_credentials(private)
            assert tomllib.loads((private/'config.toml').read_text())=={
                'model_provider':'fixture','features':{'multi_agent':False}}
            (account/'config.toml').write_text('[')
            try:prepare_credentials(root/'private-bad-config')
            except tomllib.TOMLDecodeError:pass
            else:raise AssertionError('Malformed existing account configuration was silently ignored')
    print('CREDENTIAL_CONTEXT_CHECK_PASS: optional config, transport-only settings, private file modes, malformed-config rejection; model_calls=0')


def run():
    credential_checks()
    with tempfile.TemporaryDirectory(prefix='chip-portability-') as temporary:
        root=Path(temporary);project=root/'project';workspace=project/'attempt';private=root/'private'
        (workspace/'spec').mkdir(parents=True);(workspace/'rtl').mkdir();private.mkdir()
        (workspace/'spec/contract.txt').write_text('own contract')
        control=project/'.chip_nebula/shared/run-control.json';control.parent.mkdir(parents=True)
        control.write_text('{"extension_seconds":0}')
        hidden=root/'other-trial-answer.txt';hidden.write_text('not exposed')
        context=private_context(project,'generation','trial-1')
        assert context==private_context(project,'generation','trial-1')
        assert context!=private_context(root/'other-project','generation','trial-1')
        assert context!=private_context(project,'ppa','trial-1')
        assert not context.is_relative_to(project)
        probe='''from pathlib import Path
import subprocess,json
p=Path.cwd()
assert (p/'spec/contract.txt').read_text()=='own contract'
try:(p/'spec/contract.txt').write_text('changed')
except OSError:pass
else:raise AssertionError('Contract writable')
assert not Path(HIDDEN).exists()
try:Path(CONTROL).write_text('extended')
except OSError:pass
else:raise AssertionError('Runtime deadline control writable')
(p/'rtl/probe.sv').write_text('module probe; initial begin $display("PORTABLE_TOOL_PASS"); $finish; end endmodule')
subprocess.run(['iverilog','-g2012','-s','probe','-o','rtl/sim','rtl/probe.sv'],check=True)
assert 'PORTABLE_TOOL_PASS' in subprocess.check_output(['vvp','rtl/sim'],text=True)
compiled=subprocess.run(['verilator','--binary','--timing','-Wno-fatal','-j','1',
    '--top-module','probe','--Mdir','rtl/verilated','rtl/probe.sv'],text=True,capture_output=True)
assert compiled.returncode==0,compiled.stdout+compiled.stderr
assert 'PORTABLE_TOOL_PASS' in subprocess.check_output(['rtl/verilated/Vprobe'],text=True)
version=subprocess.check_output(['/tools/codex','--version'],text=True)
assert version.startswith('codex-cli '),version
print('PORTABLE_SANDBOX_PASS')
'''.replace('HIDDEN',repr(str(hidden))).replace('CONTROL',repr(str(control)))
        command=sandbox_command(project,workspace,private,[sys.executable,'-c',probe])
        result=subprocess.run(command,capture_output=True,text=True,timeout=60)
        if result.returncode:raise AssertionError(result.stderr+result.stdout)
        assert 'PORTABLE_SANDBOX_PASS' in result.stdout
        try:sandbox_command(project,root/'outside-workspace',private,['true'])
        except ValueError:pass
        else:raise AssertionError('Outside workspace accepted')
        try:sandbox_command(project,workspace,project/'private',['true'])
        except ValueError:pass
        else:raise AssertionError('Private context exposed in project')
    print(json.dumps({'passed':True,'model_calls':0,'physical_calls':0,
        'checks':['Icarus compile/run, Verilator C++ build/run and standalone Codex CLI actually run inside bwrap','contract read-only',
                  'other trial hidden','invalid workspace/context rejected'],
        'scope':'Portable tool discovery qualification; scored campaign retains its originally frozen helper'}))


if __name__=='__main__':run()
