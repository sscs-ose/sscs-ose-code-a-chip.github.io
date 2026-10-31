"""Native hierarchy footprints with per-instance wire estimates and report rows."""
from silk.layout import estimate_layout
import numpy as np


def estimate_hierarchy(module, routing, *, packing_factor=2.5, routing_overhead=1.2, path='tx'):
    """Use silk's footprint estimation and instance traversal for report rows."""
    options = dict(packing_factor=packing_factor, routing_overhead=routing_overhead)
    # Silk API: calculate child footprints before the parent estimate.
    root_estimate = estimate_layout(module, routing, children='estimate', **options)
    records = []
    # Silk API: traversal keeps repeated placements distinct even though their
    # definitions are shared. Reversing it puts descendants before the root.
    for instance in reversed(list(module.iter_instances(include_self=True))):
        current = instance.module
        estimate = (root_estimate if not instance.path else
                    estimate_layout(current, routing, children='reuse', **options))
        records.append({'path': f'{path}.{instance.path}' if instance.path else path,
                        'module': current, 'estimate': estimate,
                        'area_um2': float(np.prod(estimate.bounding_box))})
    return records
