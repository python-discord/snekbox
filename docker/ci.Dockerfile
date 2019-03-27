FROM pythondiscord/snekbox-base:latest

RUN mkdir -p /snekbox
COPY . /snekbox
WORKDIR /snekbox

RUN pipenv sync --dev
RUN pipenv run lint

CMD ["pipenv", "run", "snekbox"]
