import os,sys
from pathlib import Path
python=os.environ["CHIP_STUDY_PYTHON"]
if sys.executable!=python:os.execv(python,[python,__file__,*sys.argv[1:]])
sys.path.insert(0,str(Path(os.environ["CHIP_STUDY_CASE"])/"scripts"))
from run_ppa_workflow_study import tool_action
tool_action(sys.argv[1],Path.cwd())
