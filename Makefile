PYTHON ?= python
TECTONIC ?= tectonic

all: report/report.pdf slides/slides.pdf

report/report.pdf: report/report.tex report/refs.bib report/generated
	cd report && $(TECTONIC) report.tex

slides/slides.pdf: slides/slides.tex slides/refs.bib report/generated
	cd slides && $(TECTONIC) slides.tex

report/generated: src/main.py src/simulation.py src/datasets.py
	$(PYTHON) src/main.py

data:
	$(PYTHON) src/datasets.py

.PHONY: all data requirements
requirements:
	pip install -qr requirements.txt
