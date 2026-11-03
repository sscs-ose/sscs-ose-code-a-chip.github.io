from pathlib import Path
import json,sys,time
from examples.microrobot.clock import clock_case
from opentcad.device.compact import SingleDiodePV
root=Path('examples/microrobot/local_runs/clock_layout/contact_escape_v2');name=sys.argv[1];step=float(sys.argv[2])
fit=json.loads(Path('examples/microrobot/results/published/pv_fit.json').read_text())
circuit=root/('physical_clock.spice' if name.startswith('schematic') else 'clock_rc.spice')
t=time.monotonic();info,data=clock_case(root/name,circuit_path=circuit,pv_model=SingleDiodePV(**fit['fitted_terminal_model']),stop_s=.004,timestep_s=step,relative_tolerance=1e-6,pv_storage_F=2e-12,output_load_F=2e-15,measure_bias_current=False)
print(json.dumps({'case':name,'wall_s':time.monotonic()-t,'info':info,'achieved_stop_s':None if data is None else float(data[-1,0])},indent=2),flush=True)
