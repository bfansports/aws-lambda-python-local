ENV = dev
PROFILE :=
EVENT :=
DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# Helper functions
FILTER_OUT = $(foreach v,$(2),$(if $(findstring $(1),$(v)),,$(v)))
TITLE_CASE = $(shell echo $1 | cut -c1 | tr '[[:lower:]]' '[[:upper:]]')$(shell echo $1 | cut -c2-)

.PHONY: help clean dist create/% run/% test test/% deploy deploy/% _check-desc api _check-vers connect
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
	echo "Create AWS function:   make create/FUNCTION DESC='Func description'"
	echo "Package all functions: make dist"
	echo "Package a function:    make dist/FUNCTION"
	echo "Deploy all functions:  make deploy [ENV=prod] - Default ENV=dev"
	echo "Deploy a function:     make deploy/FUNCTION [ENV=prod]"
	echo "Setup environment:     make .env [ENV=environment]"
	echo "Set function MEM size: make setmem/FUNCTION SIZE=[size]" 
	echo "----------------------------------------------------------"
	echo "Deploy an API to AWS:  make api VERS=<version> [UPDATE=<api_id>] [STAGE=<stage_name>] [CREATE=1]"
	echo "                       Load the proper YAML file from ./swagger folder using the VERS provided. Processes the file to inject Variables"
	echo "                       You can also decide to deploy it straight to AWS API Gateway"
	echo "                       If UPDATE is provided: It will update the API directly in AWS using the ID provided"
	echo "                       If STAGE is provided: It will also deploy the API once updated"
	echo "                       If CREATE is provided: It will create the API"
	echo "----------------------------------------------------------"
	echo "Test a live API:       make connect METHOD=<method> ENDPOINT=</path/{id}> [QUERY=<foo=bar&bar=foo>] [PAYLOAD=<filepath>] [NOAUTH=1]"
	echo "                       METHOD: GET, POST, PUT, PATCH, DELETE, etc"
	echo "                       ENDPOINT refers to the URL path after the hostname/stage/"
	echo "                       QUERY refers to the querystring passed to the URL"
	echo "                       You can provide payload with STDIN. Launch the command and just type your input JSON data, then hit 'ctrl-d' to exit input and send the data to your API"
	echo "                       NOAUTH forces a new Cognito Identity and ignore the .identity file"
	echo ""	
	echo "                       Examples:"
	echo "                       POST /signin: Sign the user in"
	echo "                       $$> make connect ENDPOINT=/signin METHOD=POST PAYLOAD=tests/data/signin.json"
	echo ""
	echo "                       GET /assets/{asset_id}: Get an asset"
	echo "                       $$> make connect ENDPOINT=/assets/0e0d1e42ad20443c METHOD=GET"
	echo "----------------------------------------------------------"

all: dist

api: .env _check-vers
	$(eval SRC_FILE = ./swagger/api-$(VERS).yaml)
	$(eval DST_FILE = _api-$(VERS).yaml)
	cp ${SRC_FILE} ${DST_FILE}
	$(eval ORCHESTRATE_AUTH = 'Basic $(shell echo -n "${ORCHESTRATE_KEY}:" | base64)')
	sed -i "s/%ORCH_CREDS%/${ORCHESTRATE_AUTH}/g" ${DST_FILE}
	sed -i "s/%AWS_ACCOUNT%/${AWS_ACCOUNT}/g" ${DST_FILE}
# If we have a STAGE then we can also deploy live 
	if [ -n "${STAGE}" ]; then \
		$(eval STAGE2 = --deploy ${STAGE}) \
		echo "Deploy to stage: ${STAGE2}"; \
	fi;
# If We activate the UPDATE variable, we can update the API Getway API directly
# We then excute AWS tool to import file in API Gateway
	if [ -n "${UPDATE}" ]; then \
		echo "Updating API: ${UPDATE}"; \
		./swagger/aws-apigateway-importer/aws-api-import.sh -u ${UPDATE} ${STAGE2} ${DST_FILE} 2>&1; \
	elif [ -n "${CREATE}" ]; then \
		echo "Creating new API"; \
		./swagger/aws-apigateway-importer/aws-api-import.sh -c ${DST_FILE} 2>&1; \
	fi;

connect: _check-connect .env
	PYTHONPATH="${DIR}build" python ${DIR}connect.py  $(if $(METHOD),-m $(METHOD)) $(if $(ENDPOINT),-p $(ENDPOINT)) $(if $(QUERY),-q $(QUERY)) $(if $(PAYLOAD),-i $(PAYLOAD)) $(if $(VERBOSE),--verbose) $(if $(NOAUTH), --noauth)

run/%: .env src/%/* build/setup.cfg $(wildcard lib/**/*) 
	PYTHONPATH="${DIR}build" python "${DIR}run.py" $(if $(VERBOSE),--verbose) $* $(if $(EVENT),"$(EVENT)")

test: $(wildcard src/**/*) $(wildcard lib/**/*) $(wildcard tests/*) build/setup.cfg .env
	PYTHONPATH="${DIR}build" python -m unittest discover $(if $(VERBOSE),--verbose)
test/%: $(wildcard src/**/*) $(wildcard lib/**/*) $(wildcard tests/*) build/setup.cfg .env
	PYTHONPATH="${DIR}build" python -m unittest tests.test$(call TITLE_CASE,$*) $(if $(VERBOSE),--verbose)

create/%: dist/%.zip _check-desc .env
	aws $(if ${PROFILE},--profile ${PROFILE},) s3 cp $< s3://sportarchive-${ENV}-code/lambda/$(<F)
	aws $(if ${PROFILE},--profile ${PROFILE},) lambda create-function \
		--function-name $* \
		--memory-size 1536 \
		--runtime python2.7 \
		--role arn:aws:iam::${AWS_ACCOUNT}:role/lambda_orchestrate_role \
		--handler index.handler \
		--code S3Bucket=sportarchive-${ENV}-code,S3Key=lambda/$(<F) \
		--description '${DESC}' \
		--timeout 10
setmem/%: _check-size
	aws $(if ${PROFILE},--profile ${PROFILE},) lambda update-function-configuration \
		--function-name $* \
		--memory-size ${SIZE}
deploy: $(addprefix deploy/,$(call FILTER_OUT,__init__, $(notdir $(wildcard src/*)))) .env
deploy/%: dist/%.zip .env
	aws $(if ${PROFILE},--profile ${PROFILE},) s3 cp $< s3://sportarchive-${ENV}-code/lambda/$(<F)
	aws $(if ${PROFILE},--profile ${PROFILE},) lambda update-function-code \
		--function-name $* \
		--s3-bucket sportarchive-${ENV}-code \
		--s3-key lambda/$(<F)
dist: $(addprefix dist/,$(addsuffix .zip,$(call FILTER_OUT,__init__, $(notdir $(wildcard src/*))))) .env
dist/%.zip: src/%/* build/setup.cfg $(wildcard lib/**/*) .env
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
	-$(RM) -f .env

.env:
	aws $(if ${PROFILE},--profile ${PROFILE},) s3 cp s3://sportarchive-${ENV}-code/${ENV}_creds ./lib/env.py
	cp ./lib/env.py .env

_check-vers:
ifndef VERS
	@echo "You must provide a Version for your API to deploy!";
	@echo "e.g: make api VERS=0.6";
	@echo "We pick the proper file in ./swagger/api-$VERSION.yaml";
	@false;
endif

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

_check-connect:
ifndef METHOD
	@echo "You must provide a METHOD variable";
	@echo "e.g: make connect METHOD=POST ENDPOINT=/signin PAYLOAD=tests/data/signin.json";
	@false;
endif
ifndef ENDPOINT
	@echo "You must provide a BASEURL variable";
	@echo "e.g: make connect METHOD=POST ENDPOINT=/signin";
	@false;
endif
