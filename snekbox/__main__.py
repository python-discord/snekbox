import argparse
import sys

from snekbox import NsJail


def parse_args() -> argparse.Namespace:
    """Parse the command-line arguments and return the populated namespace."""
    parser = argparse.ArgumentParser(
        prog="snekbox",
        usage="%(prog)s [-h] code [nsjail_args ...] [--- py_args ...]",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("code", help="the Python code to evaluate")
    parser.add_argument(
        "nsjail_args",
        nargs="*",
        default=[],
        help="override configured NsJail options",
    )
    parser.add_argument(
        "py_args",
        nargs="*",
        default=["-c"],
        help="arguments to pass to the Python process",
    )
    # nsjail_args and py_args are just dummies for documentation purposes.
    # Their actual values come from all the unknown arguments.
    # There doesn't seem to be a better solution with argparse.

    # Split sys.argv based on '---' separator
    if "---" in sys.argv:
        separator_index = sys.argv.index("---")
        args_before = sys.argv[1:separator_index]
        args_after = sys.argv[separator_index + 1 :]
    else:
        args_before = sys.argv[1:]
        args_after = None

    # Parse only the first positional argument (code) and known flags
    args, unknown = parser.parse_known_args(args_before[:1] if args_before else [])

    # Everything after 'code' and before '---' goes to nsjail_args
    args.nsjail_args = args_before[1:] if len(args_before) > 1 else []

    # Everything after '---' goes to py_args
    if args_after is not None:
        args.py_args = args_after
    else:
        args.py_args = ["-c"]

    return args


def main() -> None:
    """Evaluate Python code through NsJail."""
    args = parse_args()
    result = NsJail().python3(py_args=[*args.py_args, args.code], nsjail_args=args.nsjail_args)
    print(result.stdout)

    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":  # pragma: no cover
    main()
