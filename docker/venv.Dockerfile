FROM ghcr.io/python-discord/snekbox-base:latest

ARG DEV
ENV PIP_NO_CACHE_DIR=false \
    PIPENV_DONT_USE_PYENV=1 \
    PIPENV_HIDE_EMOJIS=1 \
    PIPENV_NOSPIN=1

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
