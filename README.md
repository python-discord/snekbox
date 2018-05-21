# snekbox
Python sandbox runners for executing code in isolation

# Dependencies

| dep    | version (or greater) |
|--------|----------------------|
| python | 3.6.5                |
| pip    | 10.0.1               |
| pipenv | 2018.05.18           |
| docker | 18.03.1-ce           |


## Setup local test

install python packages

```bash
pipenv sync
```

Start a rabbitmq instance and get the container IP

```bash
docker run --name rmq -d rabbitmq:3.7.5-alpine
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' rmq
# expected output with default setting: 172.17.0.2
# If not, change the runner/config.py file to match
```

## Test the code

use two terminals!

```bash
#terminal 1
pipenv run python runner/consume.py

#terminal 2
pipenv run python runner/publish.py
```

The publish will put a message on the message queue
and the consumer will pick it up and do stuff

## Build and run the consumer in a container

```bash
docker build -t snekbox:latest -f docker/Dockerfile .

#terminal 1
docker run --name snekbox -d snekbox:latest
docker logs snekbox -f

#terminal 2
pipenv run python runner/publish.py
```
