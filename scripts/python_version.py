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


ALL_VERSIONS: list[Version] = []
"""A list of all versions available for eval."""
MAIN_VERSION: Version = None
"""The default eval version, and the version used by the server."""
VERSION_DISPLAY_NAMES: list[str] = []
"""The display names for all available eval versions."""

if MAIN_VERSION is None:
    # Set the constants' values the first time the file is imported
    for version_json in json.loads(VERSIONS_FILE.read_text("utf-8")):
        version = Version(**version_json)
        if version.is_main:
            MAIN_VERSION = version
        ALL_VERSIONS.append(version)
        VERSION_DISPLAY_NAMES.append(version.display_name)

    if MAIN_VERSION is None:
        raise Exception("Exactly one version must be configured as the main version.")
