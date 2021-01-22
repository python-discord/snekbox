[![Discord][5]][6]
[![Build Status][1]][2]
[![Coverage Status][3]][4]
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

# snekbox

Python sandbox runners for executing code in isolation aka snekbox.

A client sends Python code to a snekbox, the snekbox executes the code, and finally the results of the execution are returned to the client.

```
          +-------------+           +-----------+
 input -> |             |---------->|           | >----------+
          |  HTTP POST  |           |  SNEKBOX  |  execution |
result <- |             |<----------|           | <----------+
          +-------------+           +-----------+
             ^                         ^
             |                         |- Executes python code
             |                         |- Returns result
             |                         +-----------------------
             |
             |- HTTP POST Endpoint receives request and returns result
             +---------------------------------------------------------

```

The code is executed in a Python process that is launched through [NsJail], which is responsible for sandboxing the Python process. See [`snekbox.cfg`] for the NsJail configuration.

The output returned by snekbox is truncated at around 1 MB.

## HTTP REST API

Communication with snekbox is done over a HTTP REST API. The framework for the HTTP REST API is [Falcon] and the WSGI being used is [Gunicorn]. By default, the server is hosted on `0.0.0.0:8060` with two workers.

See [`snekapi.py`] and [`resources`] for API documentation.

## Running snekbox

A Docker image is available in the [GitHub Container Registry]. A container can be started with the following command, which will also pull the image if it doesn't currently exist locally:

```
docker run --ipc=none --privileged -p 8060:8060 ghcr.io/python-discord/snekbox
```

To run it in the background, use the `-d` option. See the documentation on [`docker run`] for more information.

The above command will make the API accessible on the host via `http://localhost:8060/`. Currently, there's only one endpoint: `http://localhost:8060/eval`.

## Third-party Packages

By default, the Python interpreter has no access to any packages besides the
standard library. Even snekbox's own dependencies like Falcon and Gunicorn are
not exposed.

To expose third-party Python packages during evaluation, install them to a custom user site:

```sh
docker exec snekbox /bin/sh -c 'PYTHONUSERBASE=/snekbox/user_base pip install numpy'
```

In the above command, `snekbox` is the name of the running container. The name may be different and can be checked with `docker ps`.

The packages will be installed to the user site within `/snekbox/user_base`. To persist the installed packages, a volume for the directory can be created with Docker. For an example, see [`docker-compose.yml`].

If `pip`, `setuptools`, or `wheel` are dependencies or need to be exposed, then use the `--ignore-installed` option with pip. However, note that this will also re-install packages present in the custom user site, effectively making caching it futile. Current limitations of pip don't allow it to ignore packages extant outside the installation destination.

## Development Environment

### Initial Setup

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

### Running snekbox

The Docker image can be built with:

```
pipenv run build
```

Use Docker Compose to start snekbox:

```
docker-compose up
```

### Running Tests

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

### Coverage

To see a coverage report, run

```
pipenv run report
```

Alternatively, a report can be generated as HTML:

```
pipenv run coverage html
```

The HTML will output to `./htmlcov/` by default


### The `devsh` Helper Script

This script starts a `bash` shell inside the venv Docker container and attaches to it. Unlike the production image, the venv image that is built by this script contains dev dependencies too. The project directory is mounted inside the container so any filesystem changes made inside the container affect the actual local project.

#### Usage

```
pipenv run devsh [--build [--clean]] [bash_args ...]
```

* `--build` Build the venv Docker image
* `--clean` Clean up dangling Docker images (only works if `--build` precedes it)
* `bash_args` Arguments to pass to `/bin/bash` (for example `-c "echo hello"`). An interactive shell is launched if no arguments are given

#### Invoking NsJail

A shell alias named `nsjpy` is included and is basically `nsjail python -c <args>` but NsJail is configured as it would be if snekbox invoked it (such as the time and memory limits). It provides an easy way to run Python code inside NsJail without the need to run snekbox with its webserver and send HTTP requests. Example usage:

```bash
nsjpy "print('hello world!')"
```

The alias can be found in `./scripts/.profile`, which is automatically added when the shell is launched in the container.

[1]: https://github.com/python-discord/snekbox/workflows/Lint,%20Test,%20Build,%20Push/badge.svg?branch=master
[2]: https://github.com/python-discord/snekbox/actions?query=workflow%3A%22Lint%2C+Test%2C+Build%2C+Push%22+branch%3Amaster
[3]: https://coveralls.io/repos/github/python-discord/snekbox/badge.svg?branch=master
[4]: https://coveralls.io/github/python-discord/snekbox?branch=master
[5]: https://raw.githubusercontent.com/python-discord/branding/master/logos/badge/badge_github.svg
[6]: https://discord.gg/python
[`snekbox.cfg`]: config/snekbox.cfg
[`snekapi.py`]: snekbox/api/snekapi.py
[`resources`]: snekbox/api/resources
[`docker-compose.yml`]: docker-compose.yml
[`docker run`]: https://docs.docker.com/engine/reference/commandline/run/
[nsjail]: https://github.com/google/nsjail
[falcon]: https://falconframework.org/
[gunicorn]: https://gunicorn.org/
[GitHub Container Registry]: https://github.com/orgs/python-discord/packages/container/package/snekbox
[pipenv]: https://docs.pipenv.org/en/latest/
