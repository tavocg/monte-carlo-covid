PYTHON ?= python

data:
	$(PYTHON) scripts/download_datasets.py

.PHONY: requirements
requirements:
	pip install -qr requirements.txt
