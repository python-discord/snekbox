FROM python:3.8.0-alpine3.10 as builder
RUN apk add --no-cache --update  \
        bison~=3.3 \
        bsd-compat-headers~=0.7 \
        flex~=2.6 \
        g++~=8.3 \
        gcc~=8.3 \
        git~=2.22 \
        libnl3-dev~=3.4 \
        linux-headers~=4.19 \
        make~=4.2 \
        protobuf-dev~=3.6
RUN git clone https://github.com/google/nsjail.git /nsjail \
    && cd /nsjail \
    && git checkout 0b1d5ac03932c140f08536ed72b4b58741e7d3cf
WORKDIR /nsjail
RUN make

FROM python:3.8.0-alpine3.10
ENV PIP_NO_CACHE_DIR=false
RUN apk add --no-cache --update \
        libnl3~=3.4 \
        libstdc++~=8.3 \
        protobuf~=3.6
RUN pip install pipenv==2018.11.26
COPY --from=builder /nsjail/nsjail /usr/sbin/
RUN chmod +x /usr/sbin/nsjail
