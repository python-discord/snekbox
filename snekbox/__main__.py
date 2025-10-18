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
        "--nsjail-args",
        nargs="*",
        default=[],
        dest="nsjail_args",
        help="override configured NsJail options (default: [])",
    )
    parser.add_argument(
        "--py-args",
        nargs="*",
        default=["-c"],
        dest="py_args",
        help="arguments to pass to the Python process (default: ['-c'])",
    )
    # nsjail_args and py_args are just dummies for documentation purposes.
    # Their actual values come from all the unknown arguments.
    # There doesn't seem to be a better solution with argparse.
    args, unknown = parser.parse_known_args()
    try:
        # Can't use double dash because that has special semantics for argparse already.
        split = unknown.index("---")
        args.nsjail_args = unknown[:split]
        args.py_args = unknown[split + 1 :]
    except ValueError:
        args.nsjail_args = unknown

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
