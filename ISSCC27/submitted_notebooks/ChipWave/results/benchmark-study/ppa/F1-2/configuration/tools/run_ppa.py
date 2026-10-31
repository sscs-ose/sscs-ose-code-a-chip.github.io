import os,sys
from pathlib import Path
python=os.environ['CHIP_STUDY_PYTHON']
if sys.executable!=python:os.execv(python,[python,__file__,*sys.argv[1:]])
if sys.argv[1]=='validate':
 from benchmark_ppa_proposal import local
 local(Path.cwd());print('PPA_CANDIDATE_VALID');raise SystemExit(0)
sys.path.insert(0,str(Path(os.environ['CHIP_STUDY_CASE'])/'scripts'))
from run_benchmark_ppa import tool_action
tool_action(sys.argv[1],Path.cwd())
