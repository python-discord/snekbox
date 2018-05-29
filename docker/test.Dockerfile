FROM alpine:3.7

RUN mkdir -p /nsjail
COPY ./nsjail.patch /nsjail/nsjail.patch

RUN apk add --no-cache libstdc++ protobuf
RUN apk add --no-cache --virtual=.nsjail-build-deps bison bsd-compat-headers build-base flex git linux-headers protobuf-dev
RUN git clone --depth=1 --branch=2.5 https://github.com/google/nsjail.git /nsjail
RUN cd /nsjail
RUN patch -p1 < /nsjail.patch
RUN make
RUN mv /nsjail/nsjail /usr/sbin
RUN rm -rf /nsjail /nsjail.patch
RUN apk del --purge .nsjail-build-deps

CMD ["/usr/sbin/nsjail", "-Mo", "--user", "99999", "--group", "99999", "--chroot", "/", "--", "/bin/sh"]
