# Development Environment

## Initial Setup

A Python 3.10 interpreter and the [pipenv] package are required. Once those requirements are satisfied, install the project's dependencies:

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

Use Docker Compose to start snekbox in development mode. The optional `--build` argument can be passed to force the image to be rebuilt.

```
docker-compose up
```

The container has all development dependencies. The repository on the host is mounted within the container; changes made to local files will also affect the container.

To build a normal container that can be used in production, run

```
pipenv run build
```

Refer to the [README] for how to run the container normally.

## Running Tests

Tests are run through coverage.py using unittest. To run the tests within a development container, run

```
pipenv run test
```

## Coverage

To see a coverage report, run

```
pipenv run report
```

Alternatively, a report can be generated as HTML with

```
pipenv run coverage html
```

The HTML will output to `./htmlcov/` by default.

The report cannot be generated on Windows directly due to the difference in file separators in the paths. Instead, launch a shell in the container (see below) and use `coverage report` or `coverage html` (do not invoke through Pipenv).

## Launching a Shell in the Container

A bash shell can be launched in the development container using

```
pipenv run devsh
```

This creates a new container which will get deleted once the shell session ends.

It's possible to run a command directly; it supports the same arguments that `bash` supports.

```bash
pipenv run devsh -c 'echo hello'
```

### Invoking NsJail

NsJail can be invoked in a more direct manner that does not require using a web server or its API. See `python -m snekbox --help`. Example usage:

```bash
python -m snekbox 'print("hello world!")' --time_limit 0 --- -m timeit
```

With this command, NsJail uses the same configuration normally used through the web API. It also has an alias, `pipenv run eval`.

## Updating NsJail

Updating NsJail mainly involves two steps:

1. Change the version used by the `git clone` command in the [Dockerfile]
2. Use `pipenv run protoc` to generate new Python code from the config protobuf

Other things to look out for are breaking changes to NsJail's config format, its command-line interface, or its logging format. Additionally, dependencies may have to be adjusted in the Dockerfile to get a new version to build or run.

[pipenv]: https://docs.pipenv.org/en/latest/
[readme]: README.md
[Dockerfile]: Dockerfile
