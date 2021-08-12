FROM debian:buster-slim as builder
RUN apt-get -y update \
    && apt-get install -y \
        bison=2:3.3.* \
        flex=2.6.* \
        g++=4:8.3.* \
        gcc=4:8.3.* \
        git=1:2.20.* \
        libprotobuf-dev=3.6.* \
        libnl-route-3-dev=3.4.* \
        make=4.2.* \
        pkg-config=0.29-6 \
        protobuf-compiler=3.6.* \
        build-essential \
        gdb \
        lcov \
        libbz2-dev \
        libffi-dev \
        libgdbm-dev \
        liblzma-dev \
        libncurses5-dev \
        libreadline6-dev \
        libsqlite3-dev \
        libssl-dev \
        lzma \
        lzma-dev \
        tk-dev \
        uuid-dev \
        zlib1g-dev
RUN git clone \
    -b '2.9' \
    --single-branch \
    --depth 1 \
    https://github.com/google/nsjail.git /nsjail
WORKDIR /nsjail
RUN make

# Build and install python
RUN git clone \
    --branch 3.10 \
    --depth 1 \
    https://github.com/python/cpython.git /python
WORKDIR /python
RUN ./configure \
#    --enable-optimizations \
    --with-ensurepip=install \
    --prefix=/python/build
RUN make -j 8
RUN make install

# ------------------------------------------------------------------------------
FROM debian:buster-slim as base

# Everything will be a user install to allow snekbox's dependencies to be kept
# separate from the packages exposed during eval.
ENV PATH=/root/.local/bin:$PATH \
    PIP_NO_CACHE_DIR=false \
    PIP_USER=1 \
    PIPENV_DONT_USE_PYENV=1 \
    PIPENV_HIDE_EMOJIS=1 \
    PIPENV_NOSPIN=1

RUN apt-get -y update \
    && apt-get install -y \
        gcc=4:8.3.* \
        libnl-route-3-200=3.4.* \
        libprotobuf17=3.6.* \
        make=4.2.* \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv
COPY --from=builder /python/build /python
RUN ls /python
RUN ls /python/bin
RUN ls /python/build
RUN /python/bin/pip3 install pipenv==2020.11.15

COPY --from=builder /nsjail/nsjail /usr/sbin/
RUN chmod +x /usr/sbin/nsjail

# ------------------------------------------------------------------------------
FROM base as venv

COPY Pipfile Pipfile.lock /snekbox/
WORKDIR /snekbox

# Pipenv installs to the default user site since PIP_USER is set.
RUN pipenv install --deploy --system

# This must come after the first pipenv command! From the docs:
# All RUN instructions following an ARG instruction use the ARG variable
# implicitly (as an environment variable), thus can cause a cache miss.
ARG DEV

# Install numpy when in dev mode; one of the unit tests needs it.
RUN if [ -n "${DEV}" ]; \
    then \
        pipenv install --deploy --system --dev \
        && PYTHONUSERBASE=/snekbox/user_base pip3 install numpy~=1.19; \
    fi

# At the end to avoid re-installing dependencies when only a config changes.
# It's in the venv image because the final image is not used during development.
COPY config/ /snekbox/config

# ------------------------------------------------------------------------------
FROM venv

ENTRYPOINT ["gunicorn"]
CMD ["-c", "config/gunicorn.conf.py", "snekbox.api.app"]

COPY . /snekbox
WORKDIR /snekbox

# At the end to prevent it from invalidating the layer cache.
ARG git_sha="development"
ENV GIT_SHA=$git_sha
