#!/usr/bin/env sh

set -eu

URL='https://raw.githubusercontent.com/google/nsjail/2.9/config.proto'
SRC_DIR='snekbox'
FILE_NAME='config'
PROTO_PATH="${SRC_DIR}/${FILE_NAME}.proto"

curl -SsL "${URL}" -o "${PROTO_PATH}"
protoc --proto_path="${SRC_DIR}" --python_out="${SRC_DIR}" "${PROTO_PATH}"

rm -f "${PROTO_PATH}"
mv -f "${SRC_DIR}/${FILE_NAME}_pb"*.py "${SRC_DIR}/${FILE_NAME}.py"
