VENV_PY := .venv/bin/python
ifeq (,$(wildcard $(VENV_PY)))
  PYTHON ?= python3
else
  PYTHON ?= $(VENV_PY)
endif

.PHONY: ml-audit
ml-audit:
	@echo "Running ML audit..."
	@mkdir -p reports
	@BMAD_MIN_IMPORTS=1 PYTHONPATH=src $(PYTHON) -m bmad_crewai.ml_audit.run --outdir reports $(ARGS)
	@echo "ML audit artefacts written to reports/"
