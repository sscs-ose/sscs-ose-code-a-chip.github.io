"""Training-only EM quality policy; independent EM acceptance stays unchanged."""
import json
import math
from pathlib import Path

import numpy as np

import multiturn_experiment as M
import xfmr_schema as XG


DEFAULT_MAX_SIGMA = 1.15


def canonical_key(geometry):
    return json.dumps(XG.normalize(geometry), sort_keys=True, separators=(',', ':'))


def training_quality(net, max_sigma=DEFAULT_MAX_SIGMA):
    """Keep raw quality findings and apply a separate, explicit training gate.

    No S-parameter projection or changes to the independent-EM threshold occur.
    Non-finite data cannot be assessed by SVD and are always rejected.
    """
    limit = float(max_sigma)
    if not math.isfinite(limit) or limit <= 0:
        raise ValueError('Training maximum singular value must be finite and positive')
    finite = bool(np.all(np.isfinite(net.s)))
    if finite:
        try:
            quality = M.network_quality(net)
        except np.linalg.LinAlgError:
            finite = False
    if not finite:
        quality = dict(reciprocity_mean=None, reciprocity_max=None,
                       max_singular_value=None, passivity_flag=True,
                       eligible_for_optimization=False,
                       note='Raw EM is retained; non-finite S or failed SVD is ineligible for training')
    sigma = quality['max_singular_value']
    reciprocal = quality['reciprocity_max']
    eligible = bool(finite and sigma is not None and reciprocal is not None
                    and math.isfinite(sigma) and math.isfinite(reciprocal)
                    and sigma <= limit and reciprocal <= .05)
    return dict(quality, eligible_for_training=eligible,
                training_max_singular_value=limit)
