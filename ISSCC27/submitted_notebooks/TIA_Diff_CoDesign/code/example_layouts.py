"""Generate and render Fig.3 layouts, including geometry-only terminal examples."""
from environment import ROOT,configure
configure()
import argparse
import ast
from datetime import datetime
import hashlib
import json
from pathlib import Path

import gdstk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch,Polygon
import numpy as np
import direct_generator_snapshot as G
import xfmr_schema as XG
from section21_parameters import INPUT_KEYS,normalize
from features14 import physical14_features
from generate_gds import terminal_parameters
import figure_style as STYLE

VARIANT='routed-return-illustration-v2'
COLORS={50:'#aeb4bc',67:'#30935b',125:'#222222',126:'#287bc1',133:'#222222',134:'#d34343',
        201:'#f0b429',202:'#9675c7',203:'#26a5a5',204:'#d65fa3'}


def read_example_parameters(notebook=None):
    """Read the notebook's single literal definition for standalone figure commands."""
    path=Path(notebook) if notebook is not None else ROOT/'TIA_CoDesign.ipynb'
    cells=json.loads(path.read_text())['cells'];definitions=[]
    for index,cell in enumerate(cells):
        if cell['cell_type']!='code':continue
        for node in ast.parse(''.join(cell['source'])).body:
            if not isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign)):continue
            targets=node.targets if isinstance(node,ast.Assign) else (node.target,)
            if any(isinstance(target,ast.Name) and target.id=='fig3_parameters' for target in targets):
                definitions.append((index,node))
    if len(definitions)!=1:
        raise ValueError('Expected one literal fig3_parameters assignment in the notebook')
    index,node=definitions[0]
    if not isinstance(node,ast.Assign) or len(node.targets)!=1:
        raise ValueError(f'Cell {index}: fig3_parameters requires a single literal assignment')
    try:
        rows=ast.literal_eval(node.value)
    except (ValueError,TypeError,SyntaxError) as error:
        raise ValueError(f'Cell {index}: fig3_parameters must be a list or tuple literal') from error
    if not isinstance(rows,(list,tuple)) or len(rows)!=6:
        raise ValueError(f'Cell {index}: fig3_parameters requires six rows')
    parameters=[]
    for row_index,row in enumerate(rows):
        if not isinstance(row,(list,tuple)) or len(row)!=len(INPUT_KEYS):
            raise ValueError(f'Cell {index}, row {row_index+1}: expected fourteen values in INPUT_KEYS order')
        try:
            parameters.append(normalize(dict(zip(INPUT_KEYS,row,strict=True)),integer_positions=True))
        except ValueError as error:
            raise ValueError(f'Cell {index}, row {row_index+1}: {error}') from error
    return parameters


def records_from_parameters(parameters):
    """Map physical inputs to the preserved winding generators without changing values."""
    parameters=list(parameters)
    if len(parameters)!=6:raise ValueError('Fig. 3 requires six physical-input records')
    records=[]
    for panel,values in zip('abcdef',parameters,strict=True):
        p=normalize(values,integer_positions=True)
        winding={key:p[key] for key in ('w','wp','s','ns','np','m','D','gap')}
        winding.update(ring_w=30.,port_backing=1)
        record=dict(panel=panel,parameters=p,em_evaluated=False,surrogate_source_compatible=False)
        if p['topology']==0:
            # Historical source np=0 represents the physical one-pass partial ring.
            winding.update(topology=0,np=0,pb=p['pb'],sb=p['sb'],u=p['u'])
            record.update(gds=f'fig3_{panel}.gds',source_parameters=XG.normalize(winding))
            record['source_parameters']['u']=p['u']
        else:
            if (p['sb'],p['pb'],p['ps'])!=(1,3,0):
                raise ValueError('Direct examples require broadside coupling, top primary return and right secondary return')
            winding.update(topology=3,pb=0,sb=1,u=0)
            record.update(gds=f'fig3_{panel}_ports.gds',winding_parameters=XG.normalize(winding),
                          layout_variant=VARIANT,terminal_positions={key:p[key] for key in ('u','us')})
            record['winding_parameters']['u']=0
        records.append(record)
    return records


def layer_polygons(cell,layer):
    return [p for p in cell.get_polygons() if p.layer==layer and p.datatype==0]



def shifted_layout(record):
    if record.get('layout_variant')!=VARIANT:raise ValueError('Unsupported illustration variant')
    # Start from the recorded source geometry, then reroute its return ends.
    winding=XG.normalize({key:record['winding_parameters'][key] for key in XG.KEYS})
    if winding['topology']!=3:raise ValueError('Terminal examples require the direct-exit winding family')
    lib,cell,nets,ports,settings=G.build_from_geometry(winding,name=Path(record['gds']).stem)
    physical=normalize(record['parameters'],integer_positions=True)
    positions={key:physical[key] for key in ('u','us')}
    if any(isinstance(record['terminal_positions'][key],(bool,np.bool_)) or record['terminal_positions'][key]!=positions[key] for key in positions):
        raise ValueError('Terminal positions disagree with the requested integer inputs')
    for value in positions.values():
        if not np.isfinite(value) or not 0<=value<=100:raise ValueError('Use a finite terminal percentage in 0..100')
    xp=positions['u']*winding['D']/100
    ys=positions['us']*winding['D']/100
    for net,layer,width in (('A',G.TM1,winding['wp']),('B',G.TM2,winding['w'])):
        points=list(settings['paths'][net])
        if net=='A':points[:2]=[(xp,points[0][1]),(xp,winding['D'])]
        else:points[-1]=(points[-1][0],ys)
        # Replace the complete path; retaining its old lead would leave a stub.
        old=nets[net][0]
        replacement=gdstk.FlexPath(points,width,joins='miter',ends=(width/2,width/2),layer=layer).to_polygons()
        if len(replacement)!=1:raise ValueError('Expected one continuous winding path')
        cell.remove(old);cell.add(*replacement)
        nets[net][0]=replacement[0];settings['paths'][net]=points
    for name,layer,key,net,width in (('P-',202,'u','A',winding['wp']),('S-',204,'us','B',winding['w'])):
        old_x,old_y,_=ports[name]
        new_x,new_y=(xp,old_y) if key=='u' else (old_x,ys)
        bounds=np.array(((old_x-width/2,old_y-width/2),(old_x+width/2,old_y+width/2)))
        terminal=[p for p in cell.polygons if np.allclose(p.bounding_box(),bounds,rtol=0,atol=1e-9)]
        if not any(p.layer==layer for p in terminal) or not any(p.layer==G.M4 for p in terminal):
            raise ValueError('Missing original return-terminal marker or ground landing')
        moving=list(terminal)
        if key=='us':
            # Move both via stacks and the complete horizontal Metal5 escape.
            xb=settings['paths']['B'][-1][0]
            for polygon in nets['B'][1:]:
                if polygon.bounding_box()[0][0]>=xb-max(width,settings['L'])/2-1e-9 and polygon not in moving:
                    moving.append(polygon)
        for polygon in moving:polygon.translate(new_x-old_x,new_y-old_y)
        for label in cell.labels:
            if label.text==name:label.origin=(new_x,new_y)
        ports[name]=(new_x,new_y,net)
    return lib,cell,nets,ports,settings


def verify_example(record,path):
    source=record['source_parameters'] if record['parameters']['topology']==0 else record['winding_parameters']
    measured=dict(zip(INPUT_KEYS,physical14_features([source])[0],strict=True))
    measured.update(terminal_parameters(path,record['parameters']['D']))
    for key in INPUT_KEYS:
        if not np.isclose(measured[key],record['parameters'][key],rtol=0,atol=1e-7):
            raise ValueError('Generated geometry and physical input record disagree: '+key)
    if record.get('layout_variant')==VARIANT:
        if record.get('em_evaluated') is not False or record.get('surrogate_source_compatible') is not False:
            raise ValueError('Illustrative terminal variants must remain separate from model/EM records')
        current=gdstk.read_gds(str(path)).top_level()[0]
        _,expected,nets,ports,settings=shifted_layout(record)
        specifications={(p.layer,p.datatype) for c in (current,expected) for p in c.polygons}
        for layer,datatype in specifications:
            stored=[p for p in current.polygons if (p.layer,p.datatype)==(layer,datatype)]
            generated=[p for p in expected.polygons if (p.layer,p.datatype)==(layer,datatype)]
            if gdstk.boolean(stored,generated,'xor',precision=.005):
                raise ValueError('Stored GDS differs from the routed terminal geometry')
        G.check(path,nets,ports,settings)
    return measured


def render(records,base,path):
    STYLE.configure()
    fig,axes=plt.subplots(2,3,figsize=(25,17),squeeze=False)
    for ax,record in zip(axes.flat,records):
        cell=gdstk.read_gds(str(base/record['gds'])).top_level()[0]
        for polygon in cell.get_polygons():
            if polygon.datatype==0:
                ax.add_patch(Polygon(polygon.points,facecolor=COLORS.get(polygon.layer,'#d8d8d8'),edgecolor='none',
                                     alpha=.55 if polygon.layer in (126,134) else .8))
        for layer,name in ((201,'P'),(202,'P′'),(203,'S'),(204,'S′')):
            markers=layer_polygons(cell,layer)
            if len(markers)!=1:raise ValueError('Expected one terminal marker for each label')
            x,y=np.mean(markers[0].points,axis=0)
            if name=='P':offset,ha,va=(-17,15),'right','bottom'
            elif name=='S':offset,ha,va=(-17,-15),'right','top'
            else:
                edge=record['parameters']['pb' if name=='P′' else 'ps']
                offset,ha,va={0:((13,0),'left','center'),1:((0,-15),'center','top'),
                              2:((-13,0),'right','center'),3:((0,13),'center','bottom')}[edge]
            ax.annotate(name,(x,y),xytext=offset,textcoords='offset points',ha=ha,va=va,
                        bbox=dict(facecolor='white',edgecolor='none',alpha=.88,pad=.6))
        ax.autoscale_view();ax.margins(.08);ax.set_aspect('equal')
        ax.set(xlabel='x (µm)',ylabel='y (µm)')
        STYLE.panel(ax,'('+record['panel']+')',y=-.23)
    fig.legend(handles=[Patch(facecolor=COLORS[layer],label=name,alpha=alpha) for layer,name,alpha in
        ((50,'Metal4 ground',.8),(67,'Metal5',.8),(126,'TopMetal1',.55),(134,'TopMetal2',.55))],
        loc='lower center',ncol=4,frameon=False,bbox_to_anchor=(.5,.005))
    fig.subplots_adjust(left=.06,right=.98,top=.98,bottom=.14,wspace=.32,hspace=.45)
    STYLE.save(fig,Path(path).parent,Path(path).stem);plt.close(fig)


def build(output,parameters=None,*,make_figure=True):
    records=records_from_parameters(read_example_parameters() if parameters is None else parameters)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    for record in records:
        path=output/Path(record['gds']).name
        if record.get('layout_variant')==VARIANT:
            lib,_,nets,ports,settings=shifted_layout(record)
            lib.write_gds(path,timestamp=datetime(2000,1,1))
            G.check(path,nets,ports,settings)
        else:
            lib,_,_,_,_=G.build_from_geometry(record['source_parameters'],name=path.stem)
            lib.write_gds(path,timestamp=datetime(2000,1,1))
        record['parameters']=normalize(record['parameters'],integer_positions=True)
        verify_example(record,path)
        record['gds']=path.name
        record['gds_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        path.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n')
    (output/'example_parameters.json').write_text(json.dumps(records,indent=2)+'\n')
    if make_figure:
        render(records,output,output/'figure-03.png')
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'runs/transformer_examples')
    args=parser.parse_args()
    result=build(args.output)
    print(f'Generated {len(result)} layouts without EM or circuit simulation')
