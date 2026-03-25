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
