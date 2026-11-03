"""Physical and feature-domain checks for joint transformer/spiral proposals."""
import json
import hashlib
from functools import lru_cache
from pathlib import Path

import numpy as np
import terminal_policy as TP

SPIRAL_KEYS=('w','s','n','Dx','Dy')
JOINT_FIELDS={'joint_search','spiral_geometries','spiral_model_sha256','spiral_domain_sha256','spiral_port_order','joint_binding_sha256'}


def proposal_binding(proposal):
    keys=('geometry','params','xmodel_sha256','data_domain_sha256','permutation',
          'spiral_geometries','spiral_model_sha256','spiral_domain_sha256','spiral_port_order',
          'constraints','metrics_surrogate','feasible','joint_search')
    value={key:proposal[key] for key in keys}
    value['stage_contract']=proposal.get('stage_contract')
    if 'spiral_source_basis' in proposal:value['spiral_source_basis']=proposal['spiral_source_basis']
    if 'em_refinement' in proposal:value['em_refinement']=proposal['em_refinement']
    contract=proposal.get('stage_contract')
    if TP.has_marker(proposal) or isinstance(contract,dict) and any(key in contract for key in TP.MARKER_KEYS):
        TP.require_markers(proposal)
        value.update({key:proposal[key] for key in TP.MARKER_KEYS})
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def joint_geometry(proposal):
    present=JOINT_FIELDS.intersection(proposal)
    if not present:
        if 'stage_contract' in proposal or ('physical_spiral_indices' in proposal and proposal['physical_spiral_indices'] is None):
            raise ValueError('Joint-search proposal is missing its spiral provenance')
        return None
    if present!=JOINT_FIELDS:raise ValueError('Joint proposal has incomplete spiral provenance')
    if proposal['joint_search'] is not True:raise ValueError('Invalid joint-search marker')
    if proposal['joint_binding_sha256']!=proposal_binding(proposal):
        raise ValueError('Joint proposal parameters or source identities changed')
    if proposal['spiral_port_order']!=[0,1] or set(proposal['spiral_geometries'])!={'L1','LB'}:
        raise ValueError('Expected canonical L1/Lb two-port geometries')
    for tag,geometry in proposal['spiral_geometries'].items():
        expected=[proposal['params'][f'{tag.lower()}_{key}'] for key in SPIRAL_KEYS]
        if geometry!=expected:raise ValueError('Spiral geometry and named circuit parameters disagree')
    return proposal['spiral_geometries']


class GeometryRejected(ValueError):
    """A proposed physical geometry is outside the permitted design space."""


class PredictionRejected(ValueError):
    """A finite ANN response fails the declared physical-network screen."""


def normalization_digest(model):
    values={key:np.asarray(getattr(model,key)).tolist() for key in ('xmin','xmax','ymin','ymax')}
    return hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def prediction_quality(response):
    """Screen every predicted positive frequency, including the first (1 GHz)."""
    values=np.asarray(response)
    if values.ndim!=3 or values.shape[1:]!=(2,2) or not np.isfinite(values).all():
        raise ValueError('Spiral prediction has an invalid shape or nonfinite values')
    return dict(maximum_singular_value=float(np.linalg.svd(values,compute_uv=False).max()),
        maximum_reciprocity_error=float(np.abs(values-values.transpose(0,2,1)).max()),
        checked_frequency_points=len(values),first_frequency_included=True)


@lru_cache(maxsize=24000)
def spiral_layout(geometry):
    """Check generated ports, via enclosures and signal connectivity."""
    import tempfile
    import gdstk
    import multiturn_experiment as M
    import direct_generator_snapshot as G
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'spiral.gds'
        M.make_spiral(path,'CANDIDATE',[int(value) for value in geometry])
        cells=gdstk.read_gds(str(path)).top_level()
    if len(cells)!=1:raise GeometryRejected('Expected one spiral layout cell')
    polygons=cells[0].get_polygons()
    metal={layer:[p for p in polygons if p.layer==layer and p.datatype==0] for layer in (50,126,134)}
    for layer in (201,202):
        ports=[p for p in polygons if p.layer==layer]
        if len(ports)!=1 or gdstk.boolean(ports,metal[134],'not',precision=.005):
            raise GeometryRejected('Spiral port is not fully supported by TopMetal2')
        if gdstk.boolean(ports,metal[50],'not',precision=.005):
            raise GeometryRejected('Spiral port lacks Metal4 backing')
    cuts=[p for p in polygons if p.layer==133 and p.datatype==0]
    if len(cuts)<2:raise GeometryRejected('Spiral underpass needs two via stacks')
    for cut in cuts:
        enclosure=gdstk.offset([cut],.5,join='miter',precision=.005)
        for layer in (126,134):
            if gdstk.boolean(enclosure,metal[layer],'not',precision=.005):
                raise GeometryRejected('Spiral via lacks its metal enclosure')
    signal=[p for p in polygons if p.layer in (126,133,134) and p.datatype==0]
    if len(set(G._components(signal)))!=1:
        raise GeometryRejected('Spiral signal network is disconnected')
    return True


def feature_range(model,geometries):
    values=np.asarray(model.kind.features(geometries),dtype=float)
    if values.shape!=(len(geometries),len(model.xmin)) or not np.isfinite(values).all():
        raise ValueError('Surrogate features have an invalid shape or nonfinite values')
    if np.any(values<model.xmin-1e-8) or np.any(values>model.xmax+1e-8):
        raise GeometryRejected('Candidate features lie outside the training normalization bounds')
    return values


class SpiralModels:
    def __init__(self,checkpoint,domain):
        from surrogate import Surrogate
        from expanded_direct_surrogate_flow import domain_spec
        self.model=Surrogate(str(checkpoint))
        if self.model.kind.name!='spiral' or len(self.model.xmin)!=9:
            raise ValueError('Joint inductor search requires the nine-feature spiral model')
        config=json.loads(Path(domain).read_text())
        if config.get('schema_version')!=1 or set(config.get('parameters',{}))!=set(SPIRAL_KEYS):
            raise ValueError('Spiral domain requires w, s, n, Dx and Dy')
        self.specs={tag:{key:domain_spec(config[field][key],key) for key in SPIRAL_KEYS}
            for tag,field in (('L1','l1_parameters'),('LB','parameters'))}
        if any(spec['kind']!='int' for specs in self.specs.values() for spec in specs.values()):
            raise ValueError('The recorded spiral search uses integer geometry ranges')
        self.freq=self.model.freq
        self.domain=Path(domain);self.checkpoint=Path(checkpoint);self.policy=config['l1_extrapolation_policy']
        if (self.policy.get('schema')!='L1-local-ANN-extrapolation-v1'
                or self.policy.get('allowance')!='L1_only_unvalidated_local_box'
                or self.policy.get('checkpoint_sha256')!=hashlib.sha256(self.checkpoint.read_bytes()).hexdigest()
                or self.policy.get('normalization_sha256')!=normalization_digest(self.model)
                or self.policy.get('maximum_singular_value')!=1.02 or self.policy.get('maximum_reciprocity_error')!=.05):
            raise ValueError('L1 extrapolation policy or frozen model identity changed')

    def bounds(self):
        return {f'{tag.lower()}_{key}':dict(spec) for tag,specs in self.specs.items() for key,spec in specs.items()}

    def geometries(self,params):
        return [[params[f'{tag}_{key}'] for key in SPIRAL_KEYS] for tag in ('l1','lb')]

    def validate(self,geometries):
        import spiral_gen
        from expanded_direct_surrogate_flow import domain_contains
        if len(geometries)!=2:raise ValueError('Expected explicit L1 and LB geometries')
        for tag,geometry in zip(('L1','LB'),geometries):
            if len(geometry)!=5 or any(not domain_contains(self.specs[tag][key],value)
                                       for key,value in zip(SPIRAL_KEYS,geometry)):
                raise GeometryRejected('Spiral geometry lies outside its search domain')
            if not spiral_gen.is_valid(*geometry):
                raise GeometryRejected('Spiral winding clearance is invalid')
        # Shape/schema failures propagate; a finite feature-range miss is an
        # expected geometric rejection, not a failed model evaluation.
        features=np.asarray(self.model.kind.features(np.asarray(geometries)),dtype=float)
        if features.shape!=(2,9) or not np.isfinite(features).all():raise ValueError('Spiral feature schema is invalid')
        feature_range(self.model,np.asarray([geometries[1]]))
        for geometry in geometries:spiral_layout(tuple(geometry))
        return features

    def source_basis(self,geometries):
        features=np.asarray(self.model.kind.features(np.asarray(geometries)),dtype=float)
        if features.shape!=(2,9) or not np.isfinite(features).all():raise ValueError('Spiral feature schema is invalid')
        low=np.asarray(self.model.xmin);high=np.asarray(self.model.xmax)
        span=high-low
        if np.any(span<=0):raise ValueError('Invalid frozen normalization span')
        records={}
        for tag,values in zip(('L1','LB'),features):
            records[tag]=dict(source='ANN',features=values.tolist(),ood_mask=((values<low-1e-8)|(values>high+1e-8)).tolist(),
                normalized_coordinates=((values-low)/span).tolist(),
                normalized_excess=(np.maximum(np.maximum(low-values,values-high),0)/span).tolist())
        return dict(schema=self.policy['schema'],policy=self.policy,domain_sha256=hashlib.sha256(self.domain.read_bytes()).hexdigest(),
            checkpoint_sha256=self.policy['checkpoint_sha256'],normalization_sha256=self.policy['normalization_sha256'],
            feature_region_is_validated=False,devices=records)

    def predict(self,geometries):
        self.validate(geometries)
        prediction=self.model.predict(geometries)
        if prediction.shape!=(len(geometries),len(self.freq),2,2) or not np.isfinite(prediction).all():
            raise ValueError('Spiral predictions have an invalid shape or nonfinite values')
        quality=prediction_quality(prediction[0])
        if quality['maximum_singular_value']>1.02 or quality['maximum_reciprocity_error']>.05:
            raise PredictionRejected('Finite L1 ANN response fails its declared all-frequency network screen: '+json.dumps(quality))
        return prediction


def bind_spiral_domain(checkpoint,base_domain,output):
    """Bind an explicitly retrained model without changing any search limits."""
    from surrogate import Surrogate,kind_for
    model=Surrogate(str(checkpoint))
    if model.kind.name!='spiral' or len(model.xmin)!=9:
        raise ValueError('The retrained spiral model must use the nine-feature representation')
    expected=kind_for('spiral')
    probes=np.array([[4,4,1,24,25],[10,2,1,70,128]])
    np.testing.assert_allclose(model.kind.features(probes),expected.features(probes),rtol=0,atol=0)
    np.testing.assert_allclose(model.freq,np.arange(1,101)*1e9,rtol=0,atol=1.)
    if (np.asarray(model.xmin).shape!=(9,) or not np.isfinite(model.xmin).all()
            or not np.isfinite(model.xmax).all() or np.any(model.xmax<=model.xmin)):
        raise ValueError('The retrained spiral normalization is invalid')
    predicted=model.predict(probes)
    if predicted.shape!=(2,100,2,2) or not np.isfinite(predicted).all():
        raise ValueError('The retrained spiral model has invalid outputs')
    config=json.loads(Path(base_domain).read_text())
    # Validate the supplied domain against the distributed checkpoint first.
    from environment import ROOT
    SpiralModels(ROOT/'models/spiral.pt',base_domain)
    config['l1_extrapolation_policy']['checkpoint_sha256']=hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest()
    config['l1_extrapolation_policy']['normalization_sha256']=normalization_digest(model)
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream:
        json.dump(config,stream,indent=2,allow_nan=False)
        stream.write('\n')
    SpiralModels(checkpoint,output)
    return output
