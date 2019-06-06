#!/usr/bin/env sh

# Sets up a development environment and runs a shell in a docker container.
# Usage: dev.sh [--build [--clean]] [ash_args ...]

if [ "$1" = "--build" ]; then
    shift
    printf "Building pythondiscord/snekbox-venv:dev..."

    docker build \
        -t pythondiscord/snekbox-venv:dev \
        -f docker/venv.Dockerfile \
        --build-arg DEV=1 \
        -q \
        . \
        >/dev/null \
    && printf " done!\n" || exit "$?"

    if [ "$1" = "--clean" ]; then
        shift
        dangling_imgs=$(docker images -f "dangling=true" -q)

        if [ -n "${dangling_imgs}" ]; then
            printf "Removing dangling images..."

            docker rmi $dangling_imgs >/dev/null \
            && printf " done!\n" || exit "$?"
        fi
    fi
fi

docker run \
    -it \
    --rm \
    --privileged \
    --network host \
    -h pdsnk-dev \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -e PIPENV_PIPFILE="/snekbox/Pipfile" \
    -e ENV="/snekbox-local/scripts/.profile" \
    -v "${PWD}":/snekbox-local \
    -w "/snekbox-local" \
    --entrypoint /bin/ash \
    pythondiscord/snekbox-venv:dev \
    "$@"
