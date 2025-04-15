"""
Utilities for managing binary downloads and execution.
"""

import os
import stat
import platform
import urllib.request
from typing import Optional


def download_file(url: str, destination: str) -> None:
    """
    Download a file from a URL to a local destination.

    Args:
        url: URL to download from.
        destination: Local path to save the file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)

    with urllib.request.urlopen(url) as response:
        with open(destination, 'wb') as out_file:
            out_file.write(response.read())


def ensure_executable(path: str) -> None:
    """
    Ensure a file is executable by the current user.

    Args:
        path: Path to the file to make executable.
    """
    if platform.system() != "Windows":
        # Add executable permissions for user
        current_permissions = os.stat(path).st_mode
        os.chmod(path, current_permissions | stat.S_IXUSR)
