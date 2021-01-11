import argparse

from snekbox.nsjail import NsJail


def parse_args() -> argparse.Namespace:
    """Parse the command-line arguments and return the populated namespace."""
    parser = argparse.ArgumentParser(prog="snekbox", usage="%(prog)s code [nsjail_args ...]")
    parser.add_argument("code", help="the Python code to evaluate")
    parser.add_argument("nsjail_args", nargs="?", help="override configured NsJail options")

    # nsjail_args is just a dummy for documentation purposes.
    # Its actual value comes from all the unknown arguments.
    # There doesn't seem to be a better solution with argparse.
    args, unknown = parser.parse_known_args()
    args.nsjail_args = unknown
    return args


def main() -> None:
    """Evaluate Python code through NsJail."""
    args = parse_args()
    result = NsJail().python3(args.code, *args.nsjail_args)
    print(result.stdout)


if __name__ == "__main__":
    main()
