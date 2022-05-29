# Contributing Guidelines

The Contributing Guidelines for Python Discord projects can be found [on our website](https://pydis.com/contributing.md).

# Development Environment

## Initial Setup

A Python 3.10 interpreter and `make` are required. A virtual environment is also recommended. Once that is set up, install the project's dependencies with `make setup`.

This also installs a git pre-commit hook so that the linter runs upon a commit.
Manual invocation is still possible with `make lint`.

## Running snekbox

Use `docker-compose up` to start snekbox in development mode. The optional `--build` argument can be passed to force the image to be rebuilt.

The container has all development dependencies. The repository on the host is mounted within the container; changes made to local files will also affect the container.

To build a normal container that can be used in production, run `make build`.

Refer to the [README] for how to run the container normally.

## Running Tests

Tests are run through coverage.py using unittest. To run the tests within a development container, run `make test`.

## Coverage

To see a coverage report, run `make report`.

The report cannot be generated on Windows directly due to the difference in file separators in the paths. Instead, launch a shell in the container (see below) and use `coverage report`.

## Launching a Shell in the Container

A bash shell can be launched in the development container using `make devsh`.  This creates a new container which will get deleted once the shell session ends.

### Invoking NsJail

NsJail can be invoked in a more direct manner that does not require using a web server or its API. See `python -m snekbox --help`. Example usage:

```bash
python -m snekbox 'print("hello world!")' --time_limit 0 --- -m timeit
```

With this command, NsJail uses the same configuration normally used through the web API.

## Managing Dependencies

pip-tools is used to compile required Python packages and all their transitive
dependencies. All files are located in the `requirements` directory. The `*.in` files are the input files and the `*.pip` files are the compiled outputs.

To add or change a dependency, modify the appropriate `*.in` file(s) and then run `make upgrade` to recompile. The make command compiles the files in a certain order. When adding a new `*.in` file, it should also be included in the make command. Furthermore, the new file should be constrained by the files compiled before it, and the files compiled after it should be constrained by the new file.

### Updating NsJail

Updating NsJail mainly involves two steps:

1. Change the version used by the `git clone` command in the [Dockerfile]
2. Use `python -m scripts.protoc` to generate new Python code from the config protobuf

Other things to look out for are breaking changes to NsJail's config format, its command-line interface, or its logging format. Additionally, dependencies may have to be adjusted in the Dockerfile to get a new version to build or run.

[readme]: README.md
[Dockerfile]: Dockerfile
