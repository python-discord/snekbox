#!/usr/bin/env sh

# Sets up a development environment and runs a shell in a docker container.
# Usage: dev.sh [--build [--clean]] [bash_args ...]

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

# Keep the container up in the background so it doesn't have to be restarted
# for the ownership fix.
# The volume is mounted to same the path in the container as the source
# directory on the host to ensure coverage can find the source files.
docker run \
    --tty \
    --detach \
    --name snekbox_test \
    --privileged \
    --network host \
    --hostname pdsnk-dev \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -e PIPENV_PIPFILE="/snekbox/Pipfile" \
    -e BASH_ENV="${PWD}/scripts/.profile" \
    --volume "${PWD}":"${PWD}" \
    --workdir "${PWD}"\
    --entrypoint /bin/bash \
    pythondiscord/snekbox-venv:dev \
    >/dev/null \

# Execute the given command(s)
docker exec -it snekbox_test /bin/bash --rcfile "${PWD}/scripts/.profile" "$@"

# Fix ownership of coverage file
# BusyBox doesn't support --reference for chown
docker exec \
    -it \
    -e CWD="${PWD}" \
    snekbox_test \
    /bin/bash \
    -c 'chown "$(stat -c "%u:%g" "${CWD}")" "${CWD}/.coverage"'

docker rm -f snekbox_test >/dev/null # Stop and remove the container
