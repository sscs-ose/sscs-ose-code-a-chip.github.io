"""Prepare canonical training arrays from newly generated full-port EM labels."""
from environment import ROOT, configure
configure()
import argparse
import json
from pathlib import Path

import numpy as np
import skrf as rf
import surrogate as S
import xfmr_schema as XG


def prepare(kind_name,responses,output):
    responses,output=Path(responses),Path(output)
    if output.exists():raise FileExistsError('Choose a fresh prepared-data output')
    kind=S.kind_for('xfmr','unified',3) if kind_name=='transformer' else S.KINDS['spiral']
    manifest_name='training_manifest.json' if kind_name=='transformer' else 'spiral_geometry.json'
    source=json.loads((ROOT/'data'/manifest_name).read_text())
    rows=[row for row in source['samples']
          if kind_name!='transformer' or row['split'] in ('train','val','test')]
    geometry={row['index']:([row['geometry'][key] for key in XG.KEYS]
                          if kind_name=='transformer' else row['geometry']) for row in rows}
    geos,labels,indices=[],[],[]
    for index in sorted(geometry):
        path=responses/(str(index)+('.s4p' if kind_name=='transformer' else '.s2p'))
        net=rf.Network(str(path))
        if (net.nports!=(4 if kind_name=='transformer' else 2) or len(net.f)!=1001 or
                not np.allclose(net.f,np.arange(1001)*1e8,rtol=1e-9,atol=1) or
                not np.isfinite(net.s).all() or not np.allclose(net.z0,50,rtol=0,atol=1e-6)):
            raise ValueError(f'Invalid full-frequency EM label for record {index}')
        selected=net.s[S.F_IDX]
        selected=.5*(selected+selected.swapaxes(-1,-2))
        if kind.broken(selected):raise ValueError(f'Open winding in record {index}')
        if kind_name=='transformer':
            import training_dataset_policy as Q
            if not Q.training_quality(net,1.15)['eligible_for_training']:
                raise ValueError(f'EM quality threshold failed for record {index}')
        geos.append(geometry[index]);labels.append(selected);indices.append(index)
    geo,s,idx=np.asarray(geos),np.asarray(labels),np.asarray(indices)
    x,y=kind.features(geo),kind.s_to_vec(s)
    positions={int(index):i for i,index in enumerate(idx)}
    partitions={key:np.asarray([positions[int(index)] for index in source['partition_indices'][part]],dtype=int)
                for part,key in (('train','tr'),('val','va'),('test','te'))}
    tr=partitions['tr'];xmin,xmax=x[tr].min(0),x[tr].max(0);ymin,ymax=y[tr].min(0),y[tr].max(0)
    xmax=np.where(xmax-xmin<1e-9,xmin+1,xmax);ymax=np.where(ymax-ymin<1e-9,ymin+1,ymax)
    output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(output,geo=geo,s=s,idx=idx,X=x,xn=(x-xmin)/(xmax-xmin)*2-1,
                        yn=(y-ymin)/(ymax-ymin)*2-1,xmin=xmin,xmax=xmax,ymin=ymin,ymax=ymax,**partitions)
    print(f'Prepared {len(idx)} canonical {kind_name} records with protected partitions')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=('transformer','spiral'),required=True)
    parser.add_argument('--responses',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();prepare(args.kind,args.responses,args.output)
