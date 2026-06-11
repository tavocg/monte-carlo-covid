PYTHON ?= python
TEX ?= tectonic

all: report/report.pdf

report/report.pdf: report/report.tex report/refs.bib
	$(PYTHON) src/main.py
	cd report && $(TEX) report.tex

data:
	$(PYTHON) src/datasets.py

.PHONY: all data requirements
requirements:
	pip install -qr requirements.txt
