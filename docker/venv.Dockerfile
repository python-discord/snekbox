FROM pythondiscord/snekbox-base:latest

ARG DEV
ENV PIP_NO_CACHE_DIR=false \
    PIPENV_DONT_USE_PYENV=1 \
    PIPENV_HIDE_EMOJIS=1 \
    PIPENV_NOSPIN=1 \
    PIPENV_VENV_IN_PROJECT=1

COPY Pipfile Pipfile.lock snekbox.cfg /snekbox/
WORKDIR /snekbox

RUN if [ -n "${DEV}" ]; then pipenv sync --dev; else pipenv sync; fi
