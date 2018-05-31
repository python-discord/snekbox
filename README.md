[![Build Status](https://travis-ci.com/discord-python/snekbox.svg?branch=master)](https://travis-ci.com/discord-python/snekbox)
# snekbox
Python sandbox runners for executing code in isolation aka snekbox

The user sends a piece of python code to a snekbox, the snekbox executes the code and sends the result back to the users.

```
          +-------------+           +------------+         +-----------+
 input -> |             |---------->|            |-------->|           | >----------+
          |  WEBSERVER  |           |  RABBITMQ  |         |  SNEKBOX  |  execution |
result <- |             |<----------|            |<--------|           | <----------+
          +-------------+           +------------+         +-----------+
             ^                         ^                      ^
             |                         |                      |- Executes python code
             |                         |                      |- Returns result
             |                         |                      +-----------------------
             |                         |
             |                         |- Message queues opens on demand and closes automatically
             |                         +---------------------------------------------------------
             |
             |- Uses websockets for asynchronous connection between webui and webserver
             +-------------------------------------------------------------------------

```


## Dependencies

| dep            | version (or greater) |
|----------------|:---------------------|
| python         | 3.6.5                |
| pip            | 10.0.1               |
| pipenv         | 2018.05.18           |
| docker         | 18.03.1-ce           |
| docker-compose | 1.21.2               |

## Setup local test

install python packages

```bash
apt-get install -y libprotobuf-dev #needed by nsjail
pipenv sync --dev
```

Start a rabbitmq instance and get the container IP

```bash
docker run -d --name rmq -p 15672:15672 -e RABBITMQ_DEFAULT_USER=rabbits -e RABBITMQ_DEFAULT_PASS=rabbits pythondiscord/rmq:latest
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' rmq
# expected output with default setting: 172.17.0.2
# If not, change the config.py file to match
```

rabbitmq webinterface: `http://localhost:15672`

start the webserver

```bash
docker run --name snekboxweb --network=host -d pythondiscord/snekboxweb:latest
netstat -plnt
# tcp    0.0.0.0:5000    LISTEN
```

use two terminals!

```bash
#terminal 1
pipenv run python snekbox.py

#terminal 2
pipenv run python snekweb.py
```

`http://localhost:5000`

_________________________________

# Build the containers

```bash
# Build
pipenv run buildbox
pipenv run buildweb

# Push
pipenv run pushbox
pipenv run pushweb
```

## Docker compose

Start all the containers with docker-compose

```bash
docker-compose up
```

this boots up rabbitmq, the snekbox and a webinterface on port 5000

`http://localhost:5000`
