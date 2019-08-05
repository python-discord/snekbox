FROM alpine:3.9.2 as builder
RUN apk add --no-cache --update  \
        bison \
        bsd-compat-headers \
        flex \
        g++ \
        gcc \
        git \
        libnl3-dev \
        linux-headers \
        make \
        protobuf-dev
RUN git clone --depth=1 https://github.com/google/nsjail.git /nsjail \
    && git checkout 0b1d5ac03932c140f08536ed72b4b58741e7d3cf
WORKDIR /nsjail
RUN make

FROM python:3.7.3-alpine3.9
ENV PIP_NO_CACHE_DIR=false
RUN apk add --no-cache --update \
        libnl3 \
        libstdc++ \
        protobuf
RUN pip install pipenv
COPY --from=builder /nsjail/nsjail /usr/sbin/
RUN chmod +x /usr/sbin/nsjail
