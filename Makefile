PYTHON ?= python
TECTONIC ?= tectonic

all: report/report.pdf

report/report.pdf: report/report.tex report/refs.bib report/generated
	cd report && $(TECTONIC) report.tex

report/generated: src/main.py src/simulation.py src/datasets.py
	$(PYTHON) src/main.py

data:
	$(PYTHON) src/datasets.py

.PHONY: all data requirements
requirements:
	pip install -qr requirements.txt
