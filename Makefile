ENV = dev
EVENT :=
DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# Helper functions
FILTER_OUT = $(foreach v,$(2),$(if $(findstring $(1),$(v)),,$(v)))
TITLE_CASE = $(shell echo $1 | cut -c1 | tr '[[:lower:]]' '[[:upper:]]')$(shell echo $1 | cut -c2-)

.PHONY: help clean dist create/% run/% test test/% deploy deploy/% _check-desc
.SILENT: help

help:
	echo "SA-LAMBDA MAKEFILE FUNCTIONS"
	echo "----------------------------------------------------------"
	echo "(Add VERBOSE=1 for verbose output)"
	echo "----------------------------------------------------------"
	echo "Run a function:        make run/FUNCTION [EVENT=filename]"
	echo "Run all tests:         make test"
	echo "Run a specific test:   make test/TEST"
	echo "----------------------------------------------------------"
	echo "Create AWS function:   make create/FUNCTION"
	echo "Package all functions: make dist"
	echo "Package a function:    make dist/FUNCTION"
	echo "Deploy all functions:  make deploy"
	echo "Deploy a function:     make deploy/FUNCTION"
	echo "----------------------------------------------------------"

all: dist

run/%: src/%/* build/setup.cfg $(wildcard lib/**/*)
	PYTHONPATH="${DIR}build" python "${DIR}run.py" $(if $(VERBOSE),--verbose) $*  $(if $(EVENT),"$(EVENT)")

test: $(wildcard src/**/*) $(wildcard lib/**/*) $(wildcard tests/*) build/setup.cfg
	PYTHONPATH="${DIR}build" python -m unittest discover $(if $(VERBOSE),--verbose)
test/%: $(wildcard src/**/*) $(wildcard lib/**/*) $(wildcard tests/*) build/setup.cfg
	PYTHONPATH="${DIR}build" python -m unittest tests.test$(call TITLE_CASE,$*) $(if $(VERBOSE),--verbose)

create/%: dist/%.zip _check-desc 
	aws s3 cp $< s3://sportarchive-${ENV}-code/lambda/$(<F)
	aws lambda create-function \
		--function-name $* \
		--memory-size 1536 \
		--runtime python2.7 \
		--role arn:aws:iam::441276146445:role/lambda_orchestrate_role \
		--handler index.handler \
		--code S3Bucket=sportarchive-${ENV}-code,S3Key=lambda/$(<F) \
		--description '${DESC}' \
		--timeout 10
setmem/%: _check-size 
	aws lambda update-function-configuration \
		--function-name $* \
		--memory-size ${SIZE}
deploy: $(addprefix deploy/,$(call FILTER_OUT,__init__, $(notdir $(wildcard src/*))))
deploy/%: dist/%.zip
	aws s3 cp $< s3://sportarchive-${ENV}-code/lambda/$(<F)
	aws lambda update-function-code \
		--function-name $* \
		--s3-bucket sportarchive-${ENV}-code \
		--s3-key lambda/$(<F)
dist: $(addprefix dist/,$(addsuffix .zip,$(call FILTER_OUT,__init__, $(notdir $(wildcard src/*)))))
dist/%.zip: src/%/* build/setup.cfg $(wildcard lib/**/*)
	cd build && zip -r -q ../$@ *
	zip -r -q $@ lib
	cd $(<D) && zip -r -q ../../$@ *

build/setup.cfg: requirements.txt
	find build/ -mindepth 1 -not -name setup.cfg -delete
	pip install -r $^ -t $(@D)
	touch $@

clean:
	-$(RM) -rf dist/*
	-$(RM) -rf build/*

_check-desc:
ifndef DESC
	@echo "You must provide a description for your function!";
	@echo "e.g: make create/<function> DESC='Awesome function that does great things!'";
	@false;
endif

_check-size:
ifndef SIZE
	@echo "You must provide a size for your function! See lambda console and function configuration for list of memory.";
	@echo "e.g: make setmem/<function> SIZE=512";
	@false;
endif
