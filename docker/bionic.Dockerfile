FROM ubuntu:18.04

RUN uname -r

# RUN apt-get update
# RUN apt-get install -y software-properties-common
# RUN add-apt-repository ppa:jonathonf/python-3.6
# RUN apt-get update

# RUN apt-get install -y curl
# RUN apt-get install -y python3.6
# RUN apt-get install -y python3.6-dev
# RUN apt-get install -y build-essential
# RUN apt-get install -y git

# RUN python3.6 --version
# RUN curl -s https://bootstrap.pypa.io/get-pip.py | python3.6 -
# RUN python3.6 -m pip install pipenv

# RUN apt-get -y update && apt-get install -y \
#     autoconf \
#     bison \
#     flex \
#     gcc \
#     g++ \
#     git \
#     libprotobuf-dev \
#     libtool \
#     make \
#     pkg-config \
#     protobuf-compiler \
#     && rm -rf /var/lib/apt/lists/*

# RUN git clone --depth 1 --branch 2.6 https://github.com/google/nsjail.git

# RUN cd /nsjail && make && mv /nsjail/nsjail /bin && rm -rf -- /nsjail
