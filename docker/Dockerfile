FROM pythondiscord/snekbox-base:latest

RUN mkdir -p /snekbox
COPY . /snekbox
WORKDIR /snekbox

RUN pipenv --rm
RUN pipenv sync

CMD ["pipenv", "run", "snekbox"]
