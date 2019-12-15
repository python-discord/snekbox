FROM python:3.8.0-slim-buster as builder
RUN apt-get -y update \
    && apt-get install -y \
        bison=2:3.3.* \
        flex=2.6.* \
        g++=4:8.3.* \
        gcc=4:8.3.* \
        git=1:2.20.* \
        libprotobuf-dev=3.6.* \
        libnl-route-3-dev=3.4.* \
        make=4.2.* \
        pkg-config=0.29-6 \
        protobuf-compiler=3.6.*
RUN git clone \
    -b '2.9' \
    --single-branch \
    --depth 1 \
    https://github.com/google/nsjail.git /nsjail
WORKDIR /nsjail
RUN make

FROM python:3.8.0-slim-buster
ENV PIP_NO_CACHE_DIR=false
RUN apt-get -y update \
    && apt-get install -y \
        gcc=4:8.3.* \
        libnl-route-3-200=3.4.* \
        libprotobuf17=3.6.* \
    && rm -rf /var/lib/apt/lists/*
RUN pip install pipenv==2018.11.26
COPY --from=builder /nsjail/nsjail /usr/sbin/
RUN chmod +x /usr/sbin/nsjail
