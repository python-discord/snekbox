"""
Parse and return python version information from the versions file.

The version file is read from the environment variable VERSIONS_CONFIG,
and defaults to config/versions.json otherwise.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

VERSIONS_FILE = Path(os.getenv("VERSIONS_CONFIG", "config/versions.json"))


@dataclass(frozen=True)
class Version:
    """A python image available for eval."""

    image_tag: str
    version_name: str
    display_name: str
    is_main: bool


_ALL_VERSIONS = None
_MAIN_VERSION = None


def get_all_versions() -> tuple[list[Version], Version]:
    """
    Get a list of all available versions for this evaluation.

    Returns a tuple of all versions, and the main version.
    """
    # Return a cached result
    global _ALL_VERSIONS, _MAIN_VERSION
    if _ALL_VERSIONS is not None:
        return _ALL_VERSIONS, _MAIN_VERSION

    versions = []
    main_version: Version | None = None

    for version_json in json.loads(VERSIONS_FILE.read_text("utf-8")):
        version = Version(**version_json)
        if version.is_main:
            main_version = version
        versions.append(version)

    if main_version is None:
        raise Exception("Exactly one version must be configured as the main version.")

    _ALL_VERSIONS, _MAIN_VERSION = versions, main_version
    return versions, main_version
