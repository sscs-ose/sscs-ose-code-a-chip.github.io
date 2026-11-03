"""EP on-chip learning, written the way a PyTorch training script reads.

    from cac_ep.ep import EPConfig, EPNetwork, fit

    cfg = EPConfig()
    net = EPNetwork(cfg)               # layout, masks, conductance window
    net.reset_parameters()             # initial levels: 35 % top level, 65 % bottom level
    fit(net, cfg)                      # for epoch: for image: equilibrium (free + nudge) -> update (sign rule)

The circuit model (circuit.py, solver.py, data.py) is the one in ../sim/ep_dr; this package only reorganizes the training code.
"""
import os
import sys
from pathlib import Path

# circuit.py / solver.py / data.py use bare imports, so their folder goes on sys.path.
# EP_DR_DIR overrides the default (<package>/sim/ep_dr), e.g. for tests.
_here = Path(__file__).resolve()
_ep_dr = Path(os.environ.get('EP_DR_DIR', _here.parents[1] / 'sim' / 'ep_dr'))
if str(_ep_dr) not in sys.path:
    sys.path.insert(0, str(_ep_dr))

from .config import EPConfig                      # noqa: E402
from .network import EPNetwork                    # noqa: E402
from .train import RunLog, evaluate, fit, prepare_data, train_epoch    # noqa: E402

__all__ = ['EPConfig', 'EPNetwork', 'fit', 'train_epoch', 'evaluate', 'prepare_data', 'RunLog']
