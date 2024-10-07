# syntax=docker/dockerfile:1.4
FROM buildpack-deps:bookworm as builder-nsjail

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
FROM buildpack-deps:bookworm as builder-py-base

ENV PYENV_ROOT=/pyenv \
    PYTHON_CONFIGURE_OPTS='--disable-test-modules --enable-optimizations \
        --with-lto --with-system-expat --without-ensurepip'

RUN apt-get -y update \
    && apt-get install -y --no-install-recommends \
        libxmlsec1-dev \
        tk-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone -b v2.4.14 --depth 1 https://github.com/pyenv/pyenv.git $PYENV_ROOT

COPY --link scripts/build_python.sh /

# ------------------------------------------------------------------------------
FROM builder-py-base as builder-py-3_12
RUN /build_python.sh 3.12.7
# ------------------------------------------------------------------------------
FROM builder-py-base as builder-py-3_13
RUN /build_python.sh 3.13.0rc3
# ------------------------------------------------------------------------------
FROM builder-py-base as builder-py-3_13t
# Building with all 3 of the options below causes tests to fail.
# Removing just the first means the image is a bit bigger, but we keep optimisations
# --disable-test-modules --enable-optimizations --with-lto
ENV PYTHON_CONFIGURE_OPTS='--enable-optimizations --with-lto --with-system-expat --without-ensurepip'
RUN /build_python.sh 3.13.0rc3t
RUN mv /snekbin/python/3.13 /snekbin/python/3.13t
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm as base

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
COPY --link --from=builder-py-3_12 /snekbin/ /snekbin/
COPY --link --from=builder-py-3_13 /snekbin/ /snekbin/
COPY --link --from=builder-py-3_13t /snekbin/ /snekbin/

RUN chmod +x /usr/sbin/nsjail \
    && ln -s /snekbin/python/3.12/ /snekbin/python/default

# ------------------------------------------------------------------------------
FROM base as venv

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
        && /snekbin/python/default/bin/python -m pip install --user numpy~=1.19; \
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
