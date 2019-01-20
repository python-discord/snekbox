[![pipeline status](https://gitlab.com/discord-python/projects/snekbox/badges/master/pipeline.svg)](https://gitlab.com/discord-python/projects/snekbox/commits/master) [![coverage report](https://gitlab.com/discord-python/projects/snekbox/badges/master/coverage.svg)](https://gitlab.com/discord-python/projects/snekbox/commits/master)

# snekbox

Python sandbox runners for executing code in isolation aka snekbox

The user sends a piece of python code to a snekbox, the snekbox executes the code and sends the result back to the users.

```
          +-------------+           +-----------+
 input -> |             |---------->|           | >----------+
          |  HTTP POST  |           |  SNEKBOX  |  execution |
result <- |             |<----------|           | <----------+
          +-------------+           +-----------+
             ^                         ^
             |                         |- Executes python code
             |                         |- Returns result
             |                         +-----------------------
             |
             |- HTTP POST Endpoint receives request and returns result
             +---------------------------------------------------------

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
| flask          | 1.0.2                |
| gevent         | 1.4                  |
| gunicorn       | 19.9                 |

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

Start the webserver with docker:

```bash
docker-compose up -d
```

Run locally with pipenv:
```bash
pipenv run snekbox # for debugging
```
Visit: `http://localhost:8060`
________________________________________
## Unit testing and lint

```bash
pipenv run lint
pipenv run test
```

________________________________________
## Build the containers

```bash
# Build
pipenv run buildbox
# Push
pipenv run pushbox
```
