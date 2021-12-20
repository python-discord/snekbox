#!/usr/bin/env python3
import shutil
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

SRC_DIR = Path("snekbox").resolve(strict=True)
FILE_NAME = "config"


def compile_proto(path: Path) -> None:
    """Compile a protobuf file at `path` into Python code."""
    protoc_bin = shutil.which("protoc")
    if not protoc_bin:
        print("protoc binary could not be found on PATH", file=sys.stderr)
        sys.exit(1)

    args = [protoc_bin, f"--proto_path={path.parent}", f"--python_out={SRC_DIR}", path]
    result = subprocess.run(args)

    if result.returncode != 0:
        sys.exit(result.returncode)


def get_version() -> str:
    """Get the NsJail version from the command line arguments."""
    parser = ArgumentParser(description="Compile an NsJail config protobuf into Python.")
    parser.add_argument("version", help="the NsJail version from which to get the protobuf file")
    args = parser.parse_args()

    return args.version


def main() -> None:
    """Get a config.proto for NsJail and compile it into Python."""
    version = get_version()
    url = f"https://raw.githubusercontent.com/google/nsjail/{version}/config.proto"

    with urlopen(url) as response:
        if response.status >= 400:
            print(f"Failed to retrieve config.proto: status {response.status}", file=sys.stderr)
            sys.exit(1)

        with TemporaryDirectory() as dir_name:
            file_path = Path(dir_name) / f"{FILE_NAME}.proto"
            with open(file_path, "wb") as file:
                file.write(response.read())
            compile_proto(file_path)

    if generated_py := next(SRC_DIR.glob(f"{FILE_NAME}_pb*.py"), None):
        print(f"Build output: {generated_py.absolute()}.")
    else:
        print(f"Could not find the generated Python file in {SRC_DIR}.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
