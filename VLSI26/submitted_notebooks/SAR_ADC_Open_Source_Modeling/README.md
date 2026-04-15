## Summary

Uses open-source dynamical system simulation package [PathSim](https://github.com/pathsim/pathsim)  to model a charge-redistribution SAR ADC.

The SAR ADC model includes common error sources including CDAC weight mismatch, kT/C sampling noise, comparator noise, and CDAC settling error. 

Also, the notebook uses the SAR ADC model to simulate a published background calibration algorithm (offset double conversion - see [Liu/Huang/Chiu Publication](https://ieeexplore.ieee.org/document/5999734). 

## Instructions to Run Notebook

* Create a new python virtual environment in the same directory as `requirements.txt`
    * `python -m venv .venv`
* Activate the virtual environment
    * Run `activate` script (exact command is platform-dependent) 
* Install the dependencies
    * `pip install -r requirements.txt`
* Open Jupyter Lab and run the notebook
