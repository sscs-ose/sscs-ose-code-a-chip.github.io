.PHONY: install test train evaluate demo clean package

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --tb=short

train:
	python src/train_pinn.py --config src/config.py --epochs 500

evaluate:
	python src/evaluate.py --checkpoint data/checkpoints/best_model.pt

demo:
	python scripts/run_demo.py

notebooks:
	jupyter lab notebooks/

clean:
	rm -rf data/checkpoints/*.pt data/processed/*.pt data/exports/*.csv
	rm -rf __pycache__ src/__pycache__ tests/__pycache__
	rm -rf .pytest_cache
	find . -name "*.pyc" -delete

package:
	bash scripts/package_submission.sh

lint:
	python -m py_compile src/config.py
	python -m py_compile src/physics.py
	python -m py_compile src/pinn_model.py
	python -m py_compile src/losses.py
	python -m py_compile src/train_pinn.py
	python -m py_compile src/dataset.py
	python -m py_compile src/evaluate.py
	python -m py_compile src/fom_analysis.py
	python -m py_compile src/inverse_design.py
	python -m py_compile src/plotting.py
	python -m py_compile src/animation.py
	python -m py_compile src/interactive_ui.py
	python -m py_compile src/export_results.py
	@echo "All source files compile successfully."

all: install test train evaluate
# --- NeuroSAR amendment targets ---------------------------------------------
# Append these targets to the existing Makefile.

.PHONY: validate biomedical reproduce clean-exports nbmake

validate:
	bash scripts/validate_spice.sh

biomedical:
	jupyter nbconvert --to notebook --execute --inplace \
	    notebooks/08_Biomedical_Case_Study.ipynb

nbmake:
	pytest --nbmake --timeout=600 notebooks/07_SPICE_Validation.ipynb \
	    notebooks/08_Biomedical_Case_Study.ipynb

reproduce: clean-exports
	@echo ">>> [1/5] Setting up environment"
	bash scripts/setup_env.sh
	@echo ">>> [2/5] Running full demo (dataset → train → eval)"
	python scripts/run_demo.py --epochs 100 --samples 4000
	@echo ">>> [3/5] Running SPICE validation (notebook 07)"
	$(MAKE) validate
	@echo ">>> [4/5] Running biomedical case study (notebook 08)"
	$(MAKE) biomedical
	@echo ">>> [5/5] Running unit tests"
	pytest tests/ -v
	@echo ">>> Reproduction complete. See data/exports/ and assets/figures/"

clean-exports:
	rm -rf data/exports/*.json data/exports/*.npz
	rm -f assets/figures/spice_*.png assets/figures/metasta*.png \
	      assets/figures/biomedical_*.png
