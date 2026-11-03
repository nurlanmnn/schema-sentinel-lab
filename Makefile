PYTHON ?= .venv/bin/python
.PHONY: all setup build generate run-python run-csharp run-ts run-all test-unit test-local test-docker
all: test-local
setup:
	python3 run_local.py setup
build:
	npm run build --prefix runtimes/typescript
	dotnet build runtimes/csharp/CsharpApp.csproj --configuration Release
	$(PYTHON) -m compileall -q runtimes/python testbed/tests testbed/scripts
# Generated bindings from main are committed; regenerate only when schemas change.
generate:
	buf generate
run-python:
	$(PYTHON) runtimes/python/main.py
run-csharp:
	dotnet run --project runtimes/csharp/CsharpApp.csproj
run-ts:
	npm start --prefix runtimes/typescript
run-all: run-python run-csharp run-ts
test-unit:
	$(PYTHON) -m unittest discover -s testbed/tests -p 'test_*.py' -v
test-local:
	python3 run_local.py test
test-docker:
	./testbed/scripts/test-roundtrip.sh
