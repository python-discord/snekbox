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
| nsjail         | 2.5                  |

_________________________________________
## Setup local test

install python packages

```bash
apt-get install -y libprotobuf-dev #needed by nsjail
pipenv sync --dev
```

## NSJail

Copy the appropriate binary to an appropriate path

```bash
cp binaries/nsjail2.6-ubuntu-x86_64 /usr/bin/nsjail
chmod +x /usr/bin/nsjail
```

give nsjail a test run

```bash
# This is a workaround because nsjail can't create the directories automatically
sudo mkdir -p /sys/fs/cgroup/pids/NSJAIL \
  && mkdir -p /sys/fs/cgroup/memory/NSJAIL

nsjail -Mo \
--rlimit_as 700 \
--chroot / \
-E LANG=en_US.UTF-8 \
-R/usr -R/lib -R/lib64 \
--user nobody \
--group nogroup \
--time_limit 2 \
--disable_proc \
--iface_no_lo \
--cgroup_pids_max=1 \
--cgroup_mem_max=52428800 \
--quiet -- \
python3.6 -ISq -c "print('test')"
```

> if it fails, try without the `--cgroup_pids_max=1` and `--cgroup_mem_max=52428800`

## Development environment

Start a rabbitmq instance and get the container IP

```bash
docker-compose up -d pdrmq
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' rmq
# expected output with default setting: 172.17.0.2
# If not, change the config.py file to match
```

rabbitmq webinterface: `http://localhost:15672`

start the webserver

```bash
docker-compose up -d pdsnkweb
netstat -plnt
# tcp    0.0.0.0:5000    LISTEN
```

`http://localhost:5000`

```bash
pipenv run snekbox # for debugging
# or
docker-compose up pdsnk # for running the container
```

________________________________________
## Unit testing and lint

Make sure rabbitmq is running before running tests

```bash
pipenv run lint
pipenv run test
```

________________________________________
## Build the containers

```bash
# Build
pipenv run buildbox
pipenv run buildweb

# Push
pipenv run pushbox
pipenv run pushweb
```


