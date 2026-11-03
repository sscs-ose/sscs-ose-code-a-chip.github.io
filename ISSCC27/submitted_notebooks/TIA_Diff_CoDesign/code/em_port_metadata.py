"""Shared, explicit landing-metal contract for the EM driver and front end."""
from pathlib import Path
import hashlib
import json
import shutil

from xfmr_schema import read_info,normalize,port_layers

METALS={'TopMetal1':126,'TopMetal2':134}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_layout(path):
    text=path.read_text(encoding='utf-8-sig')
    if path.suffix=='.json':
        value=json.loads(text)
        if value.get('schema')=='em_port_definition_v1':
            if value.get('nports')!=len(value['port_layers']):raise ValueError('Port receipt count is inconsistent')
            return value['port_layers'],value.get('reference_layer'),value.get('gds_sha256')
        # A network certificate is a different record, not transformer geometry.
        if value.get('status')=='complete' and ('response_sha256' in value or 'snp_sha256' in value):return None
        if value.get('kind')=='spiral':
            if value.get('port_layers',['TopMetal2']*2)!=['TopMetal2']*2:raise ValueError('Spiral metadata has conflicting port layers')
            return ['TopMetal2']*2,'Metal4',None
        if 'parameters' not in value and 'w' not in value:
            raise ValueError(f'{path.name}: unrecognized layout metadata')
        geometry=normalize(value)
        if geometry['topology']==2 and not geometry['port_backing']:
            raise ValueError('Series-v3 EM ports require Metal4 backing')
        layers=port_layers(geometry)
        if 'port_layers' in value and value['port_layers']!=layers:
            raise ValueError(f'{path.name}: port_layers conflict with the geometry schema')
        return layers,'Metal4',value.get('gds_sha256')
    lines=text.splitlines()
    if len(lines)>1 and lines[1].strip()=='spiral':return ['TopMetal2']*2,'Metal4',None
    if len(lines)>1 and lines[1].strip()=='xfmr':
        geometry=read_info(path)
        if geometry['topology']==2 and not geometry['port_backing']:
            raise ValueError('Series-v3 EM ports require Metal4 backing')
        return port_layers(geometry),'Metal4',None
    # A sibling .log may be an EM console log. It is not geometry evidence.
    if path.parent.name=='INFO':raise ValueError(f'{path.name}: invalid INFO geometry record')
    return None


def resolve_port_metadata(gds,workdir,explicit=None,nports=None):
    gds=Path(gds).resolve();workdir=Path(workdir).resolve()
    if explicit is not None and explicit not in METALS:raise ValueError('Unsupported explicit landing metal')
    candidates=[gds.with_name(gds.stem+'.geometry.json'),gds.with_suffix('.json'),
        gds.with_name(gds.stem+'.ports.json'),gds.with_suffix('.log'),
        workdir/'INFO'/(gds.stem+'.log'),workdir/'INFO'/(gds.stem+'.json')]
    definitions=[];sources=[];seen=set()
    for path in candidates:
        if path in seen or not path.exists():continue
        seen.add(path);record=_read_layout(path)
        if record is None:continue
        layers,reference,digest=record
        if not layers or len(set(layers))!=1 or layers[0] not in METALS or reference!='Metal4':
            raise ValueError(f'{path.name}: unsupported or mixed EM landing metals')
        if digest is not None and digest!=sha(gds):raise ValueError(f'{path.name}: GDS hash does not match metadata')
        definitions.append(list(layers))
        preserved=gds.with_name(gds.stem+'.geometry.json')
        source=preserved if path==gds.with_suffix('.json') and preserved.exists() and sha(preserved)==sha(path) else path
        entry=dict(file=source.name,sha256=sha(source))
        if entry not in sources:sources.append(entry)
    if definitions and any(value!=definitions[0] for value in definitions):
        raise ValueError('Conflicting EM port definitions in layout metadata')
    if definitions:
        layers=definitions[0]
        if nports is not None and len(layers)!=nports:raise ValueError('Layout metadata and requested port count disagree')
        if explicit is not None and explicit!=layers[0]:raise ValueError('Explicit port metal conflicts with layout metadata')
    else:
        if explicit is None or nports not in (2,4):
            raise ValueError('EM landing metadata is missing; supply layout metadata or an explicit port metal and port count')
        layers=[explicit]*nports
    return dict(schema='em_port_definition_v1',nports=len(layers),port_layers=layers,reference_layer='Metal4',
        gds_file=gds.name,gds_sha256=sha(gds),metadata_sources=sources,explicit_port_metal=explicit)


def resolve_port_metal(gds,workdir,explicit=None,nports=None):
    return resolve_port_metadata(gds,workdir,explicit,nports)['port_layers'][0]


def validate_port_coverage(gds,metadata):
    """Every marker must be covered by actual ground and selected signal copper."""
    import gdstk
    cells=gdstk.read_gds(str(gds)).top_level()
    if len(cells)!=1:raise ValueError('Expected one GDS top-level cell for EM')
    polygons=cells[0].get_polygons();records=[]
    for index,metal in enumerate(metadata['port_layers'],1):
        markers=[p for p in polygons if p.layer==200+index and p.datatype==0]
        if len(markers)!=1:raise ValueError('Expected exactly one marker per EM port')
        marker=markers[0];area=marker.area()
        if area<=0:raise ValueError('EM port marker has zero area')
        for name,layer in (('Metal4',50),(metal,METALS[metal])):
            copper=[p for p in polygons if p.layer==layer and p.datatype==0]
            missing=sum(p.area() for p in gdstk.boolean(marker,copper,'not',precision=1e-5)) if copper else area
            if missing>max(1e-6,area*1e-6):raise ValueError(f'Port {index} is not covered by {name}')
        records.append(dict(port=index,reference_layer='Metal4',signal_layer=metal,copper_coverage_verified=True))
    return records


def preserve_geometry_metadata(gds,output):
    """Keep a geometry sidecar when its old name is also the EM certificate name."""
    gds=Path(gds);output=Path(output);source=gds.with_suffix('.json')
    if source.resolve()!=output.with_suffix('.json').resolve() or not source.exists():return
    if _read_layout(source) is None:raise FileExistsError('Preserve the existing EM certificate and choose a fresh output')
    target=gds.with_name(gds.stem+'.geometry.json')
    if target.exists():
        if target.read_bytes()!=source.read_bytes():raise FileExistsError('Preserved geometry metadata already differs')
    else:shutil.copyfile(source,target)
