FROM python:3.6-alpine3.7

RUN apk add --no-cache libstdc++ protobuf build-base docker

ENV PIPENV_VENV_IN_PROJECT=1
ENV PIPENV_IGNORE_VIRTUALENVS=1
ENV PIPENV_NOSPIN=1
ENV PIPENV_HIDE_EMOJIS=1
ENV PYTHONPATH=/snekbox

RUN pip install pipenv

COPY binaries/nsjail2.5-alpine-x86_64 /usr/sbin/nsjail
RUN chmod +x /usr/sbin/nsjail
