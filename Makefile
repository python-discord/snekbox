PIP_COMPILE_CMD = pip-compile -q -U

.PHONY: install-piptools
install-piptools:
	pip install -U -q -r requirements/pip-tools.pip

.PHONY: setup
setup: install-piptools
	pip-sync requirements/coverage.pip \
		requirements/lint.pip \
		requirements/requirements.pip
	pre-commit install

.PHONY: upgrade
upgrade: install-piptools
	$(PIP_COMPILE_CMD) -o requirements/requirements.pip \
		--extra gunicorn --extra sentry pyproject.toml
	$(PIP_COMPILE_CMD) -o requirements/coverage.pip requirements/coverage.in
	$(PIP_COMPILE_CMD) -o requirements/coveralls.pip requirements/coveralls.in
	$(PIP_COMPILE_CMD) -o requirements/lint.pip requirements/lint.in
	$(PIP_COMPILE_CMD) -o requirements/pip-tools.pip requirements/pip-tools.in

.PHONY: lint
lint: setup
	pre-commit run --all-files

# Fix ownership of the coverage file even if tests fail & preserve exit code
.PHONY: test
test:
	docker-compose build -q --force-rm
	docker-compose run --entrypoint /bin/bash --rm snekbox -c \
    	'coverage run -m unittest; e=$?; chown --reference=. .coverage; exit $e'

.PHONY: report
report: setup
	coverage report

.PHONY: build
build:
	docker build -t ghcr.io/python-discord/snekbox:latest .

.PHONY: devsh
devsh:
	docker-compose run --entrypoint /bin/bash --rm snekbox
