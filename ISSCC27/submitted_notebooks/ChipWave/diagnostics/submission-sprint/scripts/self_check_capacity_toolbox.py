"""Exercise quota exhaustion and actual model-tool isolation, without a model."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from capacity_toolbox import ToolBudget, execute_development, inspect_argv, sandbox_command
from study_protocol import write_json


def check():
    assert inspect_argv("rg -n 'reset|cancel' rtl")==["rg","-n","reset|cancel","rtl"]
    for command in ("rg --pre 'python evil.py' x","cat a; python evil.py",
                    "python tests/custom.py","tail -f rtl/a.sv","ls $(python evil.py)"):
        argv=inspect_argv(command)
        if argv is not None:
            # argv never undergoes shell expansion; literals cannot execute code.
            assert "$(" in command or ";" in command
    with tempfile.TemporaryDirectory(prefix="capacity-tools-") as tmp:
        root=Path(tmp);work=root/"workspace"
        for name in ("rtl","spec","tools","tests","reports","build"):
            (work/name).mkdir(parents=True)
        secret=root/"reference.txt";secret.write_text("hidden final/reference canary")
        (work/"spec/contract.txt").write_text("frozen")
        (work/"rtl/test.sv").write_text('module test; initial begin $display("SIM_PASS");$finish;end endmodule')
        probe=f"""from pathlib import Path
import socket,subprocess,os
assert not Path({str(secret)!r}).exists()
assert not Path('/home/asic03/.codex/auth.json').exists()
assert not Path('/eda').exists()
try:Path('spec/contract.txt').write_text('changed')
except OSError:pass
else:raise AssertionError('Frozen contract writable')
try:
 s=socket.create_connection(('127.0.0.1',7897),timeout=1)
except OSError:pass
else:s.close();raise AssertionError('Model tool can reach provider proxy')
assert not Path('/tools/codex').exists()
assert not Path('/tools/yosys').exists()
assert 'CAPACITY_SECRET_CANARY' not in os.environ
print('TOOL_SANDBOX_PASS')
"""
        os.environ["CAPACITY_SECRET_CANARY"]="fixture"
        try:
            process=subprocess.run(sandbox_command(work,[sys.executable,"-c",probe]),
                                   capture_output=True,text=True,timeout=20)
        finally:
            os.environ.pop("CAPACITY_SECRET_CANARY")
        assert process.returncode==0,process.stdout+process.stderr
        row,text=execute_development(work,root/"ledger","iverilog -g2012 -s test -o build/sim rtl/test.sv && vvp build/sim")
        assert row["status"]=="passed" and "SIM_PASS" in text,(row,text)
        budget=ToolBudget(root/"ledger")
        background=subprocess.run(sandbox_command(work,["/bin/bash","-c",
            "(sleep 0.2; echo escaped > reports/late) >/dev/null 2>&1 &"]),
            capture_output=True,text=True,timeout=10)
        assert background.returncode==0,background.stderr
        time.sleep(.4)
        assert not (work/"reports/late").exists(),"Detached source mutation survived tool return"
        for _ in range(19):
            identity=budget.reserve("development",{})
            budget.finish(identity,"failed","synthetic quota fixture; no actual tool run")
        try:budget.reserve("development",{})
        except ValueError:pass
        else:raise AssertionError("Twenty-first check accepted")
        for _ in range(2):
            identity=budget.reserve("physical",{})
            budget.finish(identity,"failed","synthetic quota fixture; no EDA")
        try:budget.reserve("physical",{})
        except ValueError:pass
        else:raise AssertionError("Third physical check accepted")
        try:budget.finish(1,"passed","overwrite")
        except ValueError:pass
        else:raise AssertionError("Terminal history overwritten")
        (work/"rtl/leak.sv").symlink_to(secret)
        try:execute_development(work,root/"other-ledger","true")
        except ValueError:pass
        else:raise AssertionError("Source symlink accepted")
    return dict(passed=True,model_calls=0,physical_runs=0,
                checks=["real isolated Icarus compile/simulation","hidden source/account/EDA exclusion",
                        "network proxy inaccessible","inherited secrets cleared",
                        "detached processes die before tool returns","read-only contract","shared check quota",
                        "third physical request refused","terminal evidence immutable","symlink rejected"],
                scope="Toolbox primitive; native hook/router and complete live runtime still pending")


if __name__=="__main__":
    result=check()
    write_json(Path(__file__).resolve().parents[1]/"checks/toolbox-isolation.json",result)
    print(json.dumps(result))
