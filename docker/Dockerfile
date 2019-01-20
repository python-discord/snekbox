FROM pythondiscord/snekbox-base:latest

RUN apk add --update tini

RUN mkdir -p /snekbox
COPY . /snekbox
WORKDIR /snekbox

RUN pipenv --rm
RUN pipenv sync

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["pipenv", "run", "snekbox"]
