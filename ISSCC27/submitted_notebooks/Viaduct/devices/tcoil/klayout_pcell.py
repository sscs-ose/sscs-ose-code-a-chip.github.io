"""Editable KLayout PCell for the Viaduct T-coil (library VIADUCT_SKY130).

Geometry comes from tcoil_core.build(), shared with the EM model. The read-only
RF fields (resultStatus, L1, L2, Q1, Q2, K1, K2) are written only by an
executed EM run (Viaduct `annotate`), together with the run ID and a key of the
geometry parameters it was computed for. Changing any geometry parameter makes
the key stale and the fields fall back to NOT_RUN, so results can never
describe a different geometry than the one shown.
"""
import hashlib
import importlib.util
import json
import os
import sys

try:
    import pya
except ImportError:
    import klayout.db as pya
from dataclasses import fields
from itertools import combinations


def _load_core():
    # Load the sibling tcoil_core by path under a unique name: KLayout may already
    # hold another package's `tcoil_core` (e.g. the older sky130_tcoil macro).
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tcoil_core.py")
    spec = importlib.util.spec_from_file_location("viaduct_tcoil_core", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


core = _load_core()
Parameters, build, METALS, PDK_NAME = core.Parameters, core.build, core.METALS, core.PDK_NAME

LIBRARY = {'sky130A': 'VIADUCT_SKY130'}.get(PDK_NAME, 'VIADUCT_' + PDK_NAME.upper())
CELL = 'TCoil'
RF_FIELDS = ('L1', 'L2', 'Q1', 'Q2', 'K1', 'K2')


def geometry_key(values):
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()[:12]


def insert_geometry(layout, cell, data):
    for (layer, datatype), points in data['polygons']:
        polygon = pya.DPolygon([pya.DPoint(x, y) for x, y in points]).to_itype(layout.dbu)
        cell.shapes(layout.layer(layer, datatype)).insert(polygon)
    for (layer, datatype), text, (x, y) in data['labels']:
        cell.shapes(layout.layer(layer, datatype)).insert(pya.DText(text, pya.DTrans(x, y)))


class TCoil(pya.PCellDeclarationHelper):
    def __init__(self):
        super().__init__()
        defaults = Parameters()
        descriptions = {'metalWidth': 'Metal width (um)', 'area': 'Envelope area budget (um^2)',
                        'turnSpacing': 'In-plane gap (um; 0=reference)',
                        'upperMetal': 'Upper winding and pins', 'lowerMetal': 'Lower parallel winding',
                        'upperCrossover': 'Upper crossover metals', 'lowerCrossover': 'Lower crossover metals',
                        'upperViaChain': 'Upper crossover via chain', 'lowerViaChain': 'Lower crossover via chain',
                        'parallelViaChain': 'Inter-plane parallel via chain'}
        for f in fields(Parameters):
            value = getattr(defaults, f.name)
            param = self.param(f.name, self.TypeString if isinstance(value, str) else self.TypeDouble,
                               descriptions[f.name], default=value)
            if isinstance(value, str):
                if 'ViaChain' in f.name:
                    choices = ['Auto'] + ['+'.join(f'via{k}' for k in range(i, j)) for i in range(1, 5) for j in range(i + 1, 6)]
                elif 'Crossover' in f.name:
                    choices = ['+'.join(c) for n in range(1, 4) for c in combinations(METALS, n)]
                else:
                    choices = list(METALS)
                for choice in choices:
                    param.add_choice(choice, choice)
        self.param('actualTurnSpacing', self.TypeDouble, 'Actual axial gap (um)', default=0, readonly=True)
        self.param('resultStatus', self.TypeString, 'EM status / run ID', default='NOT_RUN', readonly=True)
        for name in RF_FIELDS:
            self.param(name, self.TypeString, name + ' (EM result)', default='--', readonly=True)
        # Hidden: geometry key of the EM run the RF fields belong to.
        self.param('emKey', self.TypeString, 'EM geometry key', default='', hidden=True)

    def values(self):
        return {f.name: getattr(self, f.name) for f in fields(Parameters)}

    def coerce_parameters_impl(self):
        values = self.values()
        data = build(Parameters(**values))
        self.actualTurnSpacing = data['actualTurnSpacing']
        if self.emKey != geometry_key(values):
            self.resultStatus = 'NOT_RUN'
            for name in RF_FIELDS:
                setattr(self, name, '--')

    def display_text_impl(self):
        return f'TCoil(W={self.metalWidth:g}, A={self.area:g}, {self.upperMetal}/{self.lowerMetal})'

    def produce_impl(self):
        insert_geometry(self.layout, self.cell, build(Parameters(**self.values())))


class TCoilLibrary(pya.Library):
    def __init__(self):
        super().__init__()
        self.description = 'Viaduct %s parallel T-coil (geometry prototype)' % PDK_NAME
        self.layout().dbu = .001
        self.layout().register_pcell(CELL, TCoil())
        self.register(LIBRARY)


def register(force=False):
    """Register the library; force=True re-registers it (hot reload after code edits)."""
    existing = pya.Library.library_by_name(LIBRARY)
    if existing and not force:
        return existing
    return TCoilLibrary()


def create_variant(layout, parameters):
    lib = register()
    declaration = lib.layout().pcell_declaration(CELL)
    specs = declaration.get_parameters()
    values = [parameters.get(spec.name, spec.default) for spec in specs]
    values = declaration.coerce_parameters(layout, values)
    return layout.create_cell(CELL, LIBRARY, {spec.name: value for spec, value in zip(specs, values)})
