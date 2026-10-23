.PHONY: setup evidence-audit calibration-check readout-check notebook-check submission-preflight dense-run dense-analyze mismatch-mc physical-status all clean

setup:
	python -m pip install -r requirements.txt

evidence-audit:
	python evidence_audit.py

calibration-check:
	python pdk_calibration_analysis.py --check

readout-check:
	python readout_budget.py --check

notebook-check:
	python -c "import json,pathlib; p=pathlib.Path('PTAT_Temperature_Sensor_Code_a_Chip.ipynb'); n=json.loads(p.read_text()); assert n['nbformat']==4 and len(n['cells'])>=8"

submission-preflight: evidence-audit calibration-check readout-check notebook-check
	python submission_preflight.py

dense-run:
	python run_sky130.py --mode both --corners tt ff ss --temps=-40:125:5

dense-analyze:
	python dense_characterization.py

mismatch-mc:
	python mismatch_mc.py --samples 100 --temps=-40:125:5

physical-status:
	python physical_verification.py

all: submission-preflight

clean:
	rm -rf __pycache__ src/__pycache__ results/dense_pdk results/mismatch_mc
