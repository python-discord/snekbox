# Development Environment

## Initial Setup

A Python 3.9 interpreter and the [pipenv] package are required. Once those requirements are satisfied, install the project's dependencies:

```
pipenv sync --dev
```

Follow that up with setting up the pre-commit hook:

```
pipenv run precommit
```

Now Flake8 will run and lint staged changes whenever an attempt to commit the changes is made. Flake8 can still be invoked manually:

```
pipenv run lint
```

## Running snekbox

The Docker image can be built with:

```
pipenv run build
```

Use Docker Compose to start snekbox:

```
docker-compose up
```

## Running Tests

Tests are run through coverage.py using unittest. Before tests can run, the dev venv Docker image has to be built:

```
pipenv run builddev
```

Alternatively, the following command will build the image and then run the tests:

```
pipenv run testb
```

If the image doesn't need to be built, the tests can be run with:

```
pipenv run test
```

## Coverage

To see a coverage report, run

```
pipenv run report
```

Alternatively, a report can be generated as HTML:

```
pipenv run coverage html
```

The HTML will output to `./htmlcov/` by default


## The `devsh` Helper Script

This script starts a `bash` shell inside the venv Docker container and attaches to it. Unlike the production image, the venv image that is built by this script contains dev dependencies too. The project directory is mounted inside the container so any filesystem changes made inside the container affect the actual local project.

### Usage

```
pipenv run devsh [--build [--clean]] [bash_args ...]
```

* `--build` Build the venv Docker image
* `--clean` Clean up dangling Docker images (only works if `--build` precedes it)
* `bash_args` Arguments to pass to `/bin/bash` (for example `-c "echo hello"`). An interactive shell is launched if no arguments are given

### Invoking NsJail

NsJail can be invoked in a more direct manner that does not require using a web server or its API. See `python -m snekbox --help`. Example usage:

```bash
python -m snekbox 'print("hello world!")' --time_limit 0
```

With this command, NsJail uses the same configuration normally used through the web API. It also has an alias, `pipenv run eval`.

[pipenv]: https://docs.pipenv.org/en/latest/
