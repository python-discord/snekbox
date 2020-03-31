FROM pythondiscord/snekbox-base:latest

ARG DEV
ARG NO_LINUXFS
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

RUN if [ -z "${NO_LINUXFS}" ]; \
    then \
        mkdir linuxfs; \
        debootstrap stable linuxfs http://deb.debian.org/debian/; \
    fi

# At the end to avoid re-installing dependencies when only a config changes.
COPY config/ /snekbox/config
