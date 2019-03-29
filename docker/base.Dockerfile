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
RUN git clone --depth=1 https://github.com/google/nsjail.git /nsjail
WORKDIR /nsjail
RUN make

FROM python:3.7.3-alpine3.9
RUN apk add --no-cache --update \
        libnl3 \
        libstdc++ \
        protobuf
RUN pip install pipenv
COPY --from=builder /nsjail/nsjail /usr/sbin/
RUN chmod +x /usr/sbin/nsjail
