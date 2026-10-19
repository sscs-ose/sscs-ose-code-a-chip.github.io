# StartRight: does reset still work after normal use?

**Adnane Essoufi. Solo project. Apache-2.0.**

Reset should restore a known state after normal use. A test that starts in that
state can miss a problem. StartRight checks the state before the supply event,
then checks whether reset changed it correctly.

Open **[StartRight.ipynb](StartRight.ipynb)** and follow it in order.
For a preview without installation, open [Explore_reset.html](Explore_reset.html).
The preview uses saved data. Its buttons do not run simulations.
[START_HERE.md](START_HERE.md) gives a short evidence map.

## Run the notebook

Extract the whole project. Open a terminal in this folder. Use Python 3.12.
First check the included files:

    python verify_review.py

On Windows, use a short extraction path and install 7-Zip:

    python -m venv .venv
    ./.venv/Scripts/python.exe -m pip install -r requirements-notebook-lock-windows-py312.txt
    ./.venv/Scripts/python.exe bootstrap.py
    ./.venv/Scripts/python.exe execute_sequence_notebook.py

On Ubuntu 24.04:

    sudo apt-get update
    sudo apt-get install -y python3 python3-venv build-essential ca-certificates
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements-notebook-lock-linux-py312.txt
    .venv/bin/python bootstrap_linux.py --jobs 2
    .venv/bin/python execute_sequence_notebook.py

Setup checks ngspice 47 and pinned SKY130 source files. To reuse an installation,
set `STARTRIGHT_NGSPICE` and `STARTRIGHT_PDK`. The last command runs all ten code
cells in a new Jupyter kernel and saves their outputs. A notebook editor is
optional and is not installed by these commands. Colab has not been checked.

## What runs now, and what is saved

The main notebook makes **six new latch simulations**. Four compare the same
supply event with and without a prior write. Two test RC voltage predictions
at fixed 0.6 V and 1.2 V dips. The predictions are saved before those runs.

It then checks saved POR, guard and reference data. The audits verify file
hashes, regenerate circuit decks and repeat measurements. They do not rerun
SPICE. A completed circuit failure is a result; an incomplete simulation has
no verdict. A new run is never replaced with saved data.

## Optional details

Use the Python from the environment created above for these commands.

| Read or run | Purpose |
|---|---|
| [REUSE.md](REUSE.md) | Use the monitor on your own signals |
| [MECHANISM.md](MECHANISM.md) | Check the RC explanation and its two predictions |
| `python execute_sequence_notebook.py --reference` | Run the four-cell saved-data reference companion |
| `python reproduce_reference.py` | Run ten new reference/control simulations |
| [REFERENCE.md](REFERENCE.md) | Reference circuit, source credit and individual-case commands |
| [EVIDENCE.md](EVIDENCE.md) | Find raw data and repeat the supporting studies |
| [APPLICABILITY.md](APPLICABILITY.md) | Understand the temperature and isolated DC limits |

`python rebuild_lesson_view.py` rebuilds the browser preview from the saved
reference data. It makes no new simulations. Answer feedback checks your reading
against the evidence; it has not been evaluated as a human learning outcome.

## Limits and license

These are finite schematic simulations using real pinned device models and
ideal added passives. Gate tunnelling is disabled. Published cells keep their
documented geometry. Hardware retention and full process/voltage/temperature
coverage are unverified. Energy comparisons count startup and every source,
and compare only working circuits under the same conditions.

The code and notebooks are Apache-2.0. [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
credits reused sources. Academic references are in the main notebook.
AI assistance was used for code and explanations.
