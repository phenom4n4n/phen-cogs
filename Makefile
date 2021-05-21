PYTHON ?= python3

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

reformat:
	$(PYTHON) -m black $(ROOT_DIR)
	$(PYTHON) -m isort $(ROOT_DIR)
	$(PYTHON) -m autoflake --recursive --in-place --remove-all-unused-imports $(ROOT_DIR)

install:
	pip install -U -r requirements.txt
