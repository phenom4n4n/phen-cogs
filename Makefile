PYTHON ?= python3

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

reformat:
	$(PYTHON) -m black -l 99 $(ROOT_DIR)
#	$(PYTHON) -m isort $(ROOT_DIR)
	$(PYTHON) -m autoflake -r -i $(ROOT_DIR)

install:
	pip install -U -r requirements.txt