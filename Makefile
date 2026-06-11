PYTHON ?= python

data:
	$(PYTHON) src/datasets.py

.PHONY: requirements
requirements:
	pip install -qr requirements.txt
