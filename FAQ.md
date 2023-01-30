## Frequently Asked Questions for the IEEE SSCS Code-a-Chip Notebook Competition

This FAQ is a WIP in progress. Ideally, our FAQ should link to GitHub issues.

## FAQ
**Question:** What is the recommended way to install tools in my Notebook?

**Answer:** Since we are using Notebooks, it is necessary not to bloat your Notebook with makefiles. The tools aren't meant to be installed from their source code. To address that, the main EDA tools necessary to design your chip  have been packaged and can be simply installed as follows:

```
import os
import pathlib
import sys

!pip install matplotlib pandas pyinstaller
!apt-get install -y ruby-full time build-essential
!apt install -f libqt4-designer libqt4-xml libqt4-sql libqt4-network libqtcore4 libqtgui4
!curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
conda_prefix_path = pathlib.Path('conda-env')
site_package_path = conda_prefix_path / 'lib/python3.7/site-packages'
sys.path.append(str(site_package_path.resolve()))
CONDA_PREFIX = str(conda_prefix_path.resolve())
PATH = os.environ['PATH']
LD_LIBRARY_PATH = os.environ.get('LD_LIBRARY_PATH', '')
%env CONDA_PREFIX={CONDA_PREFIX}
%env PATH={CONDA_PREFIX}/bin:{PATH}
%env LD_LIBRARY_PATH={CONDA_PREFIX}/lib:{LD_LIBRARY_PATH}
!bin/micromamba create --yes --prefix $CONDA_PREFIX
!echo 'python ==3.7*' >> {CONDA_PREFIX}/conda-meta/pinned
!bin/micromamba install --yes --prefix $CONDA_PREFIX \
                        --channel litex-hub \
                        --channel main \
                        open_pdks.sky130a \
                        magic \
                        netgen \
                        openroad \
                        yosys
!bin/micromamba install --yes --prefix $CONDA_PREFIX \
                        --channel conda-forge \
                        tcllib gdstk pyyaml click svgutils ngspice
```
Please refer to this [template](https://github.com/chipsalliance/silicon-notebooks/blob/main/digital-inverter-openlane.ipynb) as an example on how to install the latest version of the tools.
##
**Question:** What if my question isn't answered by the FAQ?

**Answer:** Please file a GitHub issue and we will try to answer your question in more details. Pull Requests to iprove this repository are welcome.
##
**Question:** When should I send a Pull Request?

**Answer:** Please open a PR when you have included all your changes. Minor changes will be accepted before the deadline.
##
**Question:** How much details should my Notebook include?

**Answer:** Documenting your Notebook and explaining thoroughly each steps is highly recommended. The goal of this competition is to promote reuse and reproducibility. Simulation results, carefully made figures and straight to the point explanations are encouraged.
##
**Question:** Is it required to have a GDS as a result of my notebook?

**Answer:** An end-to-end flow is encouraged but not required. Focusing on the key idea as well as providing simulation graphs and documenting thoroughly your notebook would be more interesting.

##
**Question:** What if a tool has a bug or a feature is missing?

**Answer:** Describing a new idea at the schematic level using an automated modeling and/or simulation flow that works around the current open-source tools limitations are well received. 