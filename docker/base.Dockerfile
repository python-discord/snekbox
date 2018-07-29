FROM python:3.6.6-alpine3.8

RUN apk add --no-cache libstdc++ protobuf
RUN apk add --update build-base

ENV PIPENV_VENV_IN_PROJECT=1
ENV PIPENV_IGNORE_VIRTUALENVS=1
ENV PIPENV_NOSPIN=1
ENV PIPENV_HIDE_EMOJIS=1
ENV PYTHONPATH=/snekbox

RUN pip install pipenv

RUN mkdir -p /snekbox
COPY Pipfile /snekbox
COPY Pipfile.lock /snekbox
COPY . /snekbox
WORKDIR /snekbox

RUN pipenv sync --dev

RUN cp binaries/nsjail2.5-alpine-x86_64 /usr/sbin/nsjail
RUN chmod +x /usr/sbin/nsjail
