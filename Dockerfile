# syntax=docker/dockerfile:1.4
FROM buildpack-deps:bookworm AS builder-nsjail

WORKDIR /nsjail

RUN apt-get -y update \
    && apt-get install -y --no-install-recommends \
        bison\
        flex \
        libprotobuf-dev\
        libnl-route-3-dev \
        protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

RUN git clone -b master --single-branch https://github.com/google/nsjail.git . \
    && git checkout dccf911fd2659e7b08ce9507c25b2b38ec2c5800
RUN make

# ------------------------------------------------------------------------------
FROM buildpack-deps:bookworm AS builder-py-base

ENV PYENV_ROOT=/pyenv \
    PYTHON_CONFIGURE_OPTS='--disable-test-modules --enable-optimizations \
        --with-lto --without-ensurepip'

RUN apt-get -y update \
    && apt-get install -y --no-install-recommends \
        libxmlsec1-dev \
        tk-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone -b v2.6.9 --depth 1 https://github.com/pyenv/pyenv.git $PYENV_ROOT

COPY --link scripts/build_python.sh /

# ------------------------------------------------------------------------------
FROM builder-py-base AS builder-py-3_13
RUN /build_python.sh 3.13.5
# ------------------------------------------------------------------------------
FROM builder-py-base AS builder-py-3_13t
# This can't be bumped to latest until https://github.com/python/cpython/issues/135734 is resolved.
RUN /build_python.sh 3.13.2t
# ------------------------------------------------------------------------------
FROM builder-py-base AS builder-py-3_14
RUN /build_python.sh 3.14.0
# ------------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS base

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=false

RUN apt-get -y update \
    && apt-get install -y --no-install-recommends \
        gcc \
        git \
        libnl-route-3-200 \
        libprotobuf32 \
    && rm -rf /var/lib/apt/lists/*

COPY --link --from=builder-nsjail /nsjail/nsjail /usr/sbin/
COPY --link --from=builder-py-3_13 /snekbin/ /snekbin/
COPY --link --from=builder-py-3_13t /snekbin/ /snekbin/
COPY --link --from=builder-py-3_14 /snekbin/ /snekbin/

RUN chmod +x /usr/sbin/nsjail \
    && ln -s /snekbin/python/3.13/ /snekbin/python/default

# ------------------------------------------------------------------------------
FROM base AS venv

COPY --link requirements/ /snekbox/requirements/
COPY --link scripts/install_eval_deps.sh /snekbox/scripts/install_eval_deps.sh
WORKDIR /snekbox

RUN pip install -U -r requirements/requirements.pip

# This must come after the first pip command! From the docs:
# All RUN instructions following an ARG instruction use the ARG variable
# implicitly (as an environment variable), thus can cause a cache miss.
ARG DEV

# Install numpy when in dev mode; one of the unit tests needs it.
RUN if [ -n "${DEV}" ]; \
    then \
        pip install -U -r requirements/coverage.pip \
        && export PYTHONUSERBASE=/snekbox/user_base \
        && /snekbin/python/default/bin/python -m pip install --user numpy~=2.2.5; \
    fi

# At the end to avoid re-installing dependencies when only a config changes.
COPY --link config/ /snekbox/config/

ENTRYPOINT ["gunicorn"]
CMD ["-c", "config/gunicorn.conf.py"]

# ------------------------------------------------------------------------------
FROM venv

# Use a separate directory to avoid importing the source over the installed pkg.
# The venv already installed dependencies, so nothing besides snekbox itself
# will be installed. Note requirements.pip cannot be used as a constraint file
# because it contains extras, which pip disallows.
RUN --mount=source=.,target=/snekbox_src,rw \
    pip install /snekbox_src[gunicorn,sentry]
