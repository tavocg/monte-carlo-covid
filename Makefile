PYTHON ?= python
TEX ?= tectonic

all: report/report.pdf

report/report.pdf: report/report.tex report/refs.bib report/generated
	cd report && $(TEX) report.tex

report/generated:
	$(PYTHON) src/main.py

data:
	$(PYTHON) src/datasets.py

.PHONY: all data requirements
requirements:
	pip install -qr requirements.txt
