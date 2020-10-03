PYTHON ?= python3.8

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

reformat:
	$(PYTHON) -m black -l 99 $(ROOT_DIR)