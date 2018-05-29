FROM python:3.6-alpine3.7

COPY ./nsjail.patch /

RUN apk add --no-cache \
        libstdc++ \
        protobuf \
    && apk add --no-cache --virtual=.nsjail-build-deps \
        bison \
        bsd-compat-headers \
        build-base \
        flex \
        git \
        linux-headers \
        protobuf-dev \
    && git clone --depth=1 --branch=2.5 https://github.com/google/nsjail.git /nsjail \
    && cd /nsjail \
    && patch -p1 < /nsjail.patch \
    && make \
    && mv /nsjail/nsjail /usr/sbin \
    && rm -rf /nsjail /nsjail.patch \
    && apk del --purge .nsjail-build-deps

RUN apk add --update tini
RUN apk add --update build-base
RUN addgroup -g 1000 -S snek && adduser -u 1000 -S snek -G snek

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

RUN pipenv sync

RUN chown -R snek:snek /snekbox
USER snek

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["pipenv", "run", "snekbox"]
