"""Create an unused session folder, then execute and verify the inline notebook."""
from datetime import datetime,timezone
from pathlib import Path
import argparse,json,os,shutil
ROOT=Path(__file__).resolve().parents[1]


def run(base):
    from scripts.build_flow2_fresh_notebook import build
    from scripts.execute_flow2_runall_notebook import execute
    from scripts.verify_flow2_fresh import verify
    tag='fresh_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    session=Path(base).resolve()/tag;session.mkdir(parents=True,exist_ok=False)
    record={'source_root':str(ROOT),'session':str(session),'work':str(session/tag),'tag':tag}
    (ROOT/'docs/flow2_fresh_session_20261023.json').write_text(json.dumps(record,indent=2)+'\n')
    record=build()
    os.environ.update(AUTOMX_RUNALL_CACHE=str(session),AUTOMX_RUNALL_TAG=tag)
    execute(ROOT,record['notebook'])
    return verify()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',type=Path,default=Path('/media/nam/EDABK/AutoMX_CIM_fresh_runs'))
    args=parser.parse_args();run(args.base)
