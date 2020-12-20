FROM python:3.9-slim-buster as builder
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
        protobuf-compiler=3.6.*
RUN git clone \
    -b '2.9' \
    --single-branch \
    --depth 1 \
    https://github.com/google/nsjail.git /nsjail
WORKDIR /nsjail
RUN make

FROM python:3.9-slim-buster as base
ENV PIP_NO_CACHE_DIR=false

RUN apt-get -y update \
    && apt-get install -y \
        gcc=4:8.3.* \
        libnl-route-3-200=3.4.* \
        libprotobuf17=3.6.* \
    && rm -rf /var/lib/apt/lists/*
RUN pip install pipenv==2020.11.4

COPY --from=builder /nsjail/nsjail /usr/sbin/
RUN chmod +x /usr/sbin/nsjail

FROM base as venv
ARG DEV
ARG git_sha="development"

ENV PIP_NO_CACHE_DIR=false \
    PIPENV_DONT_USE_PYENV=1 \
    PIPENV_HIDE_EMOJIS=1 \
    PIPENV_NOSPIN=1 \
    GIT_SHA=$git_sha

COPY Pipfile Pipfile.lock /snekbox/
WORKDIR /snekbox

RUN if [ -n "${DEV}" ]; \
    then \
        pipenv install --deploy --system --dev; \
    else \
        pipenv install --deploy --system; \
    fi

# At the end to avoid re-installing dependencies when only a config changes.
COPY config/ /snekbox/config

FROM venv

ENTRYPOINT ["gunicorn"]
CMD ["-c", "config/gunicorn.conf.py", "snekbox.api.app"]

COPY . /snekbox
WORKDIR /snekbox
