import datetime
import subprocess

__all__ = ("get_version",)


def get_version() -> str:
    """
    Return a version based on the HEAD commit's date.

    The format is 'year.month.day.commits' and is compliant with PEP 440. 'commits' is the amount of
    commits made on the same date as HEAD, excluding HEAD. This ensures versions are unique if
    multiple release occur on the same date.
    """
    args = ["git", "show", "-s", "--format=%ct", "HEAD"]
    stdout = subprocess.check_output(args, text=True)
    timestamp = float(stdout.strip())
    date = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)

    commits = count_commits_on_date(date) - 1  # Exclude HEAD.

    # Don't use strftime because it includes leading zeros, which are against PEP 440.
    return f"{date.year}.{date.month}.{date.day}.{commits}"


def count_commits_on_date(dt: datetime.datetime) -> int:
    """Return the amount of commits made on the given UTC aware datetime."""
    dt = dt.combine(dt - datetime.timedelta(days=1), dt.max.time(), dt.tzinfo)

    # git log uses the committer date for this, not the author date.
    args = ["git", "log", "--oneline", "--after", str(dt.timestamp())]
    stdout = subprocess.check_output(args, text=True)

    return stdout.strip().count("\n")
