# Automated PMIC Generation

[![https://github.com/pmicgen/pmicgen/blob/main/jupyter/pmic.ipynb](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/pmicgen/pmicgen/blob/main/jupyter/pmic.ipynb)
[![Open in Dev Containers](https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/pmicgen/pmicgen)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
![https://github.com/psf/black](https://img.shields.io/badge/code%20style-black-000000.svg)

Automated generation of a PMIC for SKY130

> :warning: Repository under work in progress, not ready for normal usage

## Usage

Run latest build of the docker image using the command shown below.

```
docker run -d --name pmicgen-jupyter -p 8888:8888 -e GRANT_SUDO=yes ghcr.io/pmicgen/pmicgen
```

Then open `localhost:8888` in your browser to access the Jupyter notebook.

You can also build the image yourself running the `build` or `all` target in `make`

## How it works

The project provides a script to make an entire LDO based on certain specification or just certains components of it.
This script is executed in detail providing some reports inside the jupyter notebook and can serve as an example to run just the python script.


## Directory structure
    .
    ├── analysis             # Parameter calculation algorithm
    ├── cli                  # Command line interface parsing
    ├── env                  # Dependencies to be installed
    ├── docker               # Dockerfile & run scripts
    ├── generation           # Algorithms and automated generation utilities
    ├── gfcells              # GDSFactory Layouts
    ├── jupyter              # Jupyter notebook as trial
    ├── magic                # Magic VLSI Designs
    ├── pymacros             # KLayout cell library
    ├── test                 # Unit tests
    ├── thirdparty           # Submodules of external projects
    └── xschem               # Testbenchs in xschem
