FROM pythondiscord/snekbox-base:latest

ENV PIPENV_VENV_IN_PROJECT=1 \
    PIPENV_NOSPIN=1 \
    PIPENV_HIDE_EMOJIS=1

COPY Pipfile Pipfile.lock /snekbox/
WORKDIR /snekbox

RUN pipenv sync --dev
