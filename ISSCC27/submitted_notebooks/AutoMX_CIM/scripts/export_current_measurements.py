"""Export the current notebook run's selected views without implying an external audit."""
from pathlib import Path
import json,shutil


def run(root,work,parent,render,electrical,evaluated=None):
    root=Path(root).resolve();work=Path(work).resolve();exports=root/'exports';exports.mkdir(exist_ok=True)
    source=Path(parent['outputs']['gds']['path']).resolve()
    assert source.is_relative_to(work.parent),'Selected top must belong to this fresh run'
    top=exports/'AutoMX_CIM_five_block_top.gds';shutil.copy2(source,top)
    images={}
    for label,path in render['images'].items():
        path=Path(path).resolve();assert path.is_relative_to(work)
        target=exports/('AutoMX_CIM_five_block_top_'+label+'.png');shutil.copy2(path,target);images[label]=str(target)
    candidate=None
    if evaluated:
        native=json.loads((evaluated/'native/verification.json').read_text())
        physical=json.loads((evaluated/'physical_parent/verification.json').read_text())
        pictures=json.loads((evaluated/'render/verification.json').read_text())
        target=exports/'AutoMX_CIM_evaluated_candidate.gds';shutil.copy2(physical['outputs']['gds']['path'],target)
        for label,path in pictures['images'].items():shutil.copy2(path,exports/('AutoMX_CIM_evaluated_candidate_'+label+'.png'))
        candidate={'gds':str(target),'adoption':native['status'],'adopted':False}
    result={'status':'CURRENT_MEASURED_RESULTS_EXPORTED','run':str(work.parent),'execution_root':str(root),
        'top_gds':str(top),'images':images,'source_top_gds':str(source),
        'native_stimulus':electrical['contract']['stimulus'],
        'logical_native_conversions':electrical['logical_conversions'],
        'partial_decode_mismatches':electrical['partial_decode_mismatches'],
        'evaluated_candidate':candidate,
        'manifest':str(work.parent/'full_native/full_native/runall_manifest.json'),
        'scope':'Current fresh-run measurements exported by the final notebook cell. Complete cell coverage and independent release audits are recorded separately by the headless runner/finalizer.'}
    (root/'LATEST_RUN.json').write_text(json.dumps(result,indent=2)+'\n')
    (work/'current_results_export.json').write_text(json.dumps(result,indent=2)+'\n')
    print('CURRENT_TOP_GDS',top,'native transactions',result['logical_native_conversions'],'partial mismatches',result['partial_decode_mismatches'],flush=True)
    return result
