.ONESHELL: ;
.PHONY: build build_deployment_dependencies init local_env deploy deploy_prod clean

ZIP_FILE = deployment.zip

build: clean build_deployment_dependencies
	cd deployment; zip -r9 ../$(ZIP_FILE) . -x "tests/*" "schema/*" "pkgs/*"
	cd deployment/pkgs; zip -ur9 ../../$(ZIP_FILE) .
	rm -rf deployment/pkgs

build_deployment_dependencies:
	docker build -t deployment_dependencies .
	docker create --name dummy_container_1 -t deployment_dependencies
	docker cp dummy_container_1:/build/pkgs deployment/
	docker rm -f dummy_container_1

init:
	pip3 install -r requirements.txt

deploy_prod:
	@read -p "Are you sure you wish to deploy to Production [Y]: " YN; \
	$(MAKE) .deploy_prod_yn YN=$$YN

.deploy_prod_yn:
ifeq ($(YN),Y)
	$(MAKE) deploy DEPLOY_ENV=prd AWS_PROFILE=personal
else
	exit 1
endif

deploy: build
	aws lambda update-function-code \
		--profile $(AWS_PROFILE) \
		--function-name buy_the_dip \
		--zip-file fileb://$(ZIP_FILE)

clean:
	find . -name .pytest_cache -type d -print0 | xargs -0 rm -r --
	find . -name __pycache__ -type d -print0 | xargs -0 rm -r --
	rm -rf deployment/pkgs