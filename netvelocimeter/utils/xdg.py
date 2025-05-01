"""XDG Base Directory Specification."""

from dataclasses import dataclass
from enum import Enum
import os
import platform
from typing import cast


def _expand_path(path: str | None) -> str | None:
    """Expand environment variables and user directory in a path.

    Handles both Windows (%VAR%) and POSIX ($VAR) style environment variables,
    as well as the tilde (~) for user home directory.

    Args:
        path: Path to expand or None

    Returns:
        Expanded path or None if input was None
    """
    if path is None:
        return None

    # First expand environment variables
    expanded = os.path.expandvars(path)

    # Then expand user directory (handles ~)
    expanded = os.path.expanduser(expanded)

    return expanded


@dataclass
class XDGPath:
    """XDG path representation.

    Attributes:
        envvar: Environment variable name for the XDG category.
        default: Default path if the environment variable is not set.
    """

    envvar: str | None = None
    """Environment variable name for XDG category."""
    default: str | None = None
    """Default path if environment variable is not set.
    Environment variables and user home directory should be expanded.
    """

    def resolve_path(self) -> str | None:
        """Get the resolved path with environment variables expanded.

        First checks if the environment variable is set, then falls back to default.
        Expands environment variables and user directory in both cases.

        Returns:
            Resolved and expanded path, or None if no path could be resolved
        """
        if self.envvar and self.envvar in os.environ:
            return _expand_path(os.environ[self.envvar])
        return _expand_path(self.default)


@dataclass
class XDGSystemPaths:
    """XDG system paths.

    Attributes:
        windows: Windows-specific XDG paths.
        posix: POSIX-specific XDG paths.
    """

    windows: XDGPath
    """Windows-specific XDG paths."""
    posix: XDGPath
    """POSIX-specific XDG paths."""

    def resolve_path(self) -> str | None:
        """Get the resolved path for the current platform.

        Returns:
            Resolved and expanded path for current platform, or None if path can't be resolved
        """
        return (
            self.windows.resolve_path()
            if platform.system() == "Windows"
            else self.posix.resolve_path()
        )


@dataclass
class XDGCategory(Enum):
    """XDG categories and their paths."""

    DATA = XDGSystemPaths(
        windows=XDGPath(envvar="LOCALAPPDATA", default="~\\AppData\\Local"),
        posix=XDGPath(envvar="XDG_DATA_HOME", default="${HOME}/.local/share"),
    )
    """user-specific data files"""
    CONFIG = XDGSystemPaths(
        windows=XDGPath(envvar="APPDATA", default="~\\AppData\\Roaming"),
        posix=XDGPath(envvar="XDG_CONFIG_HOME", default="${HOME}/.config"),
    )
    """user-specific configuration files"""
    STATE = XDGSystemPaths(
        windows=XDGPath(envvar="LOCALAPPDATA", default="~\\AppData\\Local"),
        posix=XDGPath(envvar="XDG_STATE_HOME", default="${HOME}/.local/state"),
    )
    """user-specific state data that should persist between (application) restarts,
    but that is not important or portable enough to the user that it should be stored in DATA
    e.g. logs, recently used files, layout, etc."""
    BIN = XDGSystemPaths(
        windows=XDGPath(envvar="LOCALAPPDATA", default="~\\AppData\\Local"),
        posix=XDGPath(envvar="XDG_BIN_HOME", default="${HOME}/.local/bin"),
    )
    """user-specific executable files; might be shared between systems of different architectures"""
    CACHE = XDGSystemPaths(
        windows=XDGPath(envvar="TEMP", default="${LOCALAPPDATA}\\Temp"),
        posix=XDGPath(envvar="XDG_CACHE_HOME", default="${HOME}/.cache"),
    )
    """user-specific non-essential (cached) data"""
    RUNTIME = XDGSystemPaths(
        windows=XDGPath(envvar="TEMP", default="${LOCALAPPDATA}\\Temp"),
        posix=XDGPath(envvar="XDG_RUNTIME_DIR", default=None),
    )
    """user-specific runtime files and other file objects, e.g. sockets, named pipes.
    This directory should have strong permissions to prevent other users from accessing it.
    This directory is ephemeral and should not persist between reboots."""

    @property
    def value(self) -> XDGSystemPaths:
        """The value of the Enum member."""
        return cast(XDGSystemPaths, self._value_)

    def resolve_path(self, *path_postfixes: str) -> str:
        """Get the resolved absolute path for this XDG category on the current os with optional path postfixes.

        Will expand environment variables and user directory.

        Args:
            *path_postfixes: Optional path postfixes to append to the base path

        Returns:
            Resolved absolute XDG path for the current os with optional path postfixes

        Raises:
            ValueError: If the path couldn't be resolved

        Examples:
            >>> XDGCategory.DATA.resolve_path()
            '/home/user/.local/share'
            >>> XDGCategory.CONFIG.resolve_path("my_app")
            '/home/user/.config/my_app'
            >>> XDGCategory.CACHE.resolve_path("my_app", "images")
            '/home/user/.cache/my_app/images'
        """
        base_path = self.value.resolve_path()
        if base_path is None or not os.path.isabs(base_path):
            raise ValueError(f"Could not resolve base path for {self.name}")
        if path_postfixes:
            base_path = os.path.join(base_path, *path_postfixes)
        return base_path
