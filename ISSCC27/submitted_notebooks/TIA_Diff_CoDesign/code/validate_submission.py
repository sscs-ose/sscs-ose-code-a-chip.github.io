"""Check the data-free submission; deep checks require regenerated datasets."""
from environment import ROOT,CODE,configure
configure()
import ast
import hashlib
import json
from pathlib import Path
import re
import numpy as np


def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_design():
    import active_constraint_search as A
    import terminal_policy as TP
    import tia_sim as T
    from features14 import FEATURE_KEYS,physical14_features
    from joint_passives import joint_geometry,SpiralModels
    from vce_policy import DEVICE_NODES
    proposal=read(ROOT/'data/selected_proposal.json')
    final=read(ROOT/'data/final_design.json')
    if proposal.get('proposal_role')!='submitted_final_design':
        raise ValueError('Expected the submitted final design')
    forbidden={'trial','stage_contract','em_refinement','retarget_authorization','original_qualification_pool'}
    if forbidden.intersection(proposal):raise ValueError('The submitted point contains an archived search dependency')
    TP.require_markers(proposal);TP.require_integer_geometry(proposal['geometry'])
    if (joint_geometry(proposal)!=final['spiral_geometries'] or proposal['params']!=final['params']
            or proposal['geometry']!=final['geometry'] or proposal['permutation']!=[3,2,0,1]):
        raise ValueError('Final geometry or circuit identity mismatch')
    for key,name in (('xmodel_sha256','transformer'),('spiral_model_sha256','spiral')):
        if proposal[key]!=sha(ROOT/'models'/(name+'.pt')):raise ValueError('Model checkpoint changed')
    if proposal['spiral_domain_sha256']!=sha(ROOT/'data/spiral_search_domain.json'):
        raise ValueError('Submitted-point spiral domain changed')
    physical=physical14_features(proposal['geometry'])[0]
    np.testing.assert_allclose(physical,[final['physical_inputs'][key] for key in FEATURE_KEYS],rtol=0,atol=1e-10)
    values=np.asarray(proposal['constraints'],float)
    if values.shape!=(16,) or not np.isfinite(values).all() or np.any(values>0):
        raise ValueError('The submitted surrogate constraint vector is invalid')
    if not proposal['feasible'] or proposal['metrics_surrogate']['bw_ghz']<34.:
        raise ValueError('The submitted surrogate point misses its target')
    for tag,metrics in (('ANN',proposal['metrics_surrogate']),('EM',final['metrics_em'])):
        np.testing.assert_allclose(T.jc_of(proposal['params'],metrics['op']),metrics['jc'],rtol=0,atol=1e-12)
        if not A.feasible(proposal['params'],metrics):raise ValueError(tag+' scalar requirements fail')
        vce=[metrics['op'][c]-metrics['op'][e] for c,e in DEVICE_NODES.values()]
        limit=1.599 if tag=='ANN' else 1.6
        if not np.isfinite(vce).all() or max(vce)>limit:raise ValueError(tag+' VCE requirement fails')
    if final['metrics_em']['bw_ghz']<=32.:raise ValueError('Independent EM bandwidth must exceed32GHz')
    from surrogate import Surrogate
    import torch
    torch.set_num_threads(1)
    xf=Surrogate(str(ROOT/'models/transformer.pt'))
    if len(xf.xmin)!=14:raise ValueError('Transformer model requires fourteen inputs')
    predicted=xf.predict([proposal['geometry']])
    if predicted.shape!=(1,100,4,4) or not np.isfinite(predicted).all():
        raise ValueError('Transformer model inference failed')
    sm=SpiralModels(ROOT/'models/spiral.pt',ROOT/'data/spiral_search_domain.json')
    sm.predict(sm.geometries(proposal['params']))
    from example_layouts import read_example_parameters
    read_example_parameters()


def check(deep=False,*,package_only=False):
    if deep and package_only:raise ValueError('Choose either package-only or deep validation')
    import nbformat
    manifest=read(ROOT/'MANIFEST.json')
    for name,digest in manifest['files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Submission file changed: '+name)
    for path in ROOT.rglob('*'):
        if path.is_symlink() and not path.resolve().is_relative_to(ROOT):
            raise ValueError('Submission contains an external symlink')
    notebook=nbformat.read(ROOT/'TIA_CoDesign.ipynb',as_version=4)
    nbformat.validate(notebook)
    for cell in notebook.cells:
        if cell.cell_type=='code':ast.parse(cell.source)
        for name in re.findall(r'attachment:([^\s)]+)',cell.source):
            if name not in cell.get('attachments',{}):raise ValueError('Missing image attachment')
        for name in re.findall(r'(?<!!)\[[^\]]+\]\((?!attachment:)([^)]+)\)',cell.source):
            path=(ROOT/name).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():raise ValueError('Notebook link escapes the submission')
    check_design()
    print('PASS: manifest, notebook, embedded figures, final-point inputs, scalar requirements and model inference')
    if not deep:return
    import surrogate as S
    import torch
    regenerated_metrics={}
    for name in ('transformer','spiral'):
        path=ROOT/'runs'/(name+'_data.npz')
        if not path.is_file():raise FileNotFoundError('Deep validation requires regenerated '+str(path.relative_to(ROOT)))
        data=dict(np.load(path,allow_pickle=False))
        checkpoint=torch.load(ROOT/'models'/(name+'.pt'),map_location='cpu',weights_only=False)
        predictor=S.Surrogate(str(ROOT/'models'/(name+'.pt')))
        for part,key in (('train','tr'),('val','va'),('test','te')):
            np.testing.assert_array_equal(data['idx'][data[key]],checkpoint['split'][part])
        x=predictor.kind.features(data['geo'])
        np.testing.assert_array_equal(x,data['X'])
        np.testing.assert_allclose((x-data['xmin'])/(data['xmax']-data['xmin'])*2-1,data['xn'],rtol=0,atol=0)
        metrics=S.test_metrics(predictor,data['geo'][data['te']],data['s'][data['te']])
        saved=read(ROOT/'models'/(name+'_report.json'))
        keys=('dS_mean','dS_max_median','dS_max_p90')
        if not all(np.isfinite(metrics[key]) for key in keys):raise ValueError('Nonfinite regenerated test metric')
        regenerated_metrics[name]={'regenerated_EM_labels':{key:metrics[key] for key in keys},
                                   'recorded_reference':{key:saved[key] for key in keys}}
    print('PASS: regenerated dataset partitions, normalization and finite test metrics')
    print(json.dumps(regenerated_metrics,indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deep',action='store_true')
    parser.add_argument('--package-only',action='store_true')
    args=parser.parse_args();check(args.deep,package_only=args.package_only)
