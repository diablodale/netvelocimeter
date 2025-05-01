"""Utilities for managing binary downloads and execution."""

import inspect
import os
import platform
import stat
import tarfile
from tempfile import TemporaryDirectory
from typing import TypeVar
from urllib.parse import urlsplit
import urllib.request
import zipfile

from ..providers.base import BaseProvider
from .hash import hash_b64encode
from .xdg import XDGCategory


def verified_basename(filepath: str) -> str:
    """Validate and return the base filename of a filepath-like.

    Args:
        filepath: Path to the file to validate.

    Returns:
        The base filename of the file.

    Raises:
        ValueError: If the base filename is missing or invalid.
    """
    if not filepath or not isinstance(filepath, str):
        raise ValueError("Invalid filepath. Must be a string.")
    basename = os.path.basename(filepath)
    if not basename:
        raise ValueError(f"Missing filename in: {filepath}")
    return basename


def download_file(url: str, dest_filepath: str) -> str:
    r"""Download a URL into a local destination path+filename.

    Args:
        url: URL from which to download the file.
        dest_filepath: Local destination path+filename for the downloaded file,
            e.g. "/path/to/file.zip", "C:\path\to\file.zip", "~/path/to/file.zip".
    """
    # assert a valid basename
    verified_basename(dest_filepath)

    # construct the absolute path for the destination file
    # caution: will change relative paths to absolute paths from the current working directory
    absolute_filepath = os.path.abspath(os.path.expanduser(dest_filepath))

    # create hierarchy of directories
    os.makedirs(os.path.dirname(absolute_filepath), exist_ok=True)

    # open the URL and write the response to the file
    with urllib.request.urlopen(url) as response, open(absolute_filepath, "wb") as out_file:
        out_file.write(response.read())

    # ensure the downloaded file exists
    if not os.path.exists(absolute_filepath):
        raise RuntimeError(f"Failed to download {url} to {absolute_filepath}")
    return absolute_filepath


def ensure_executable(filepath: str) -> str:
    """Ensure a file is executable by the current user.

    This is a no-op on Windows. On Linux/MacOS it sets the executable bit.

    Args:
        filepath: Path to the file to make executable.

    Returns:
        Same value as filepath argument.
    """
    if platform.system() != "Windows":
        # Add executable permissions for user
        current_permissions = os.stat(filepath).st_mode
        os.chmod(filepath, current_permissions | stat.S_IXUSR)
    return filepath


# TODO add support for MacOS universals, bsd pkg
def extract_file(archive_filepath: str, internal_filepath: str, dest_dir: str) -> str:
    """Extract a specific file from an archive to a destination directory.

    Args:
        archive_filepath: Archive file path (.zip, .tgz, .tar.gz)
        internal_filepath: Internal archive file path to extract, e.g. "testapp", "win32/testapp.exe"
        dest_dir: Directory in which to extract the file

    Returns:
        Path to the extracted file

    Raises:
        RuntimeError: If the archive format is not supported or contains unsafe paths
    """
    # modules internally use forward slashes as directory separators to comply with tar and zip archive specs
    internal_filepath = internal_filepath.replace("\\", "/")

    # construct the final path for the extracted file
    final_path = os.path.abspath(os.path.join(dest_dir, os.path.basename(internal_filepath)))

    # Extract based on file extension; with safety checks not possible with shutil.unpack_archive
    if archive_filepath.endswith(".zip"):
        with zipfile.ZipFile(archive_filepath, "r") as zipf:
            # get info for the target file
            # module internally uses only forward slashes to comply with archive spec
            zip_info = zipf.getinfo(internal_filepath)

            # validate it is a file with size > 0
            if zip_info.is_dir() or zip_info.file_size == 0:
                raise RuntimeError(f"File {internal_filepath} is empty or not a file.")

            # directly extract and write to the final path
            with open(final_path, "wb") as out_file:
                out_file.write(zipf.read(zip_info))

    elif archive_filepath.endswith(".tgz") or archive_filepath.endswith(".tar.gz"):
        # For Linux .tgz files
        with tarfile.open(archive_filepath, "r:gz") as tarf:
            # get info for the target file
            # module internally uses only forward slashes to comply with archive spec
            tar_info = tarf.getmember(internal_filepath)

            # validate it is a file with size > 0
            if not tar_info.isfile() or tar_info.size == 0:
                raise RuntimeError(f"File {internal_filepath} is empty or not a file.")

            # custom filter that inherits from 'data' filter and flattens the path
            # to avoid directory traversal issues
            def data_flatten_filter(tarinfo: tarfile.TarInfo, dest_path: str) -> tarfile.TarInfo:
                # Flatten the file's path
                tarinfo.name = os.path.basename(tarinfo.name)

                # apply the data filter to check for absolute paths, traversal, links, devs, etc.
                tarinfo = tarfile.data_filter(tarinfo, dest_path)

                return tarinfo

            # extract with custom filter directly to final_path
            tarf.extract(tar_info, dest_dir, filter=data_flatten_filter)

    else:
        raise RuntimeError(f"Unsupported archive format: {archive_filepath}")

    # Ensure the extracted file exists
    if not os.path.exists(final_path):
        raise RuntimeError(
            f"Failed to extract {internal_filepath} from {archive_filepath} to {final_path}"
        )
    return final_path


# TypeVar for the provider class
B = TypeVar("B", bound=BaseProvider)


class BinaryManager:
    """Class for managing binary downloads and caching them."""

    def __init__(self, provider_class: type[B], custom_root: str | None = None) -> None:
        r"""Initialize the BinaryManager.

        Args:
            provider_class: Provider class (not instance), used to partition the cache.
                Must be a class that inherits from BaseProvider.
            custom_root: Custom binary cache root directory for provider binaries
              - None (default) = automatic platform-specific directory where
                posix follows XDG rules,
                windows is within `LOCALAPPDATA`
              - str = custom directory path for binary cache
        """
        # validate provider_class
        if not issubclass(provider_class, BaseProvider) or inspect.isabstract(provider_class):
            raise ValueError(
                f"Invalid provider class: {provider_class}. Must be a concrete subclass of BaseProvider."
            )

        # resolve cache_root
        if custom_root:
            # expand environment variables and user directory
            cache_root = os.path.expandvars(custom_root)
            cache_root = os.path.expanduser(cache_root)

            # check if the path is absolute
            if not os.path.isabs(cache_root):
                raise ValueError(f"Invalid custom root {custom_root}")
        else:
            # Use platform-specific XDG directory
            cache_root = XDGCategory.BIN.resolve_path("netvelocimeter")

        # Get the class name for partitioning
        provider_name = provider_class.__name__.lower()

        # create the provider-specific cache directory
        cache_root = os.path.join(cache_root, platform.system(), platform.machine(), provider_name)

        # make canonical
        cache_root = os.path.abspath(cache_root)

        # create the directory if it doesn't exist
        os.makedirs(cache_root, exist_ok=True)
        self._cache_root = cache_root

    def _cache_dir_for_url(self, url: str) -> str:
        """Create and return the cache absolute directory for a given URL.

        Args:
            url: URL for which to get the cache directory, likely just before downloading.

        Returns:
            Cache absolute directory for the URL.
        """
        # Construct the cache directory for the URL
        cache_dir = os.path.join(self._cache_root, hash_b64encode(data=url))

        # create the directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def _retrieve_from_cache(self, url: str, filename: str) -> str | None:
        """Check if the archive file exists in the cache directory.

        Args:
            url: URL for which to check the cache.
            filename: File name to seek in the cache.

        Returns:
            Absolute path to the cached file if it exists, otherwise None.
        """
        # construct the full path for a potentially cached file
        cached_filepath = os.path.join(self._cache_dir_for_url(url=url), filename)
        return cached_filepath if os.path.exists(cached_filepath) else None

    def download_extract(
        self, url: str, internal_filepath: str, dest_dir: str | None = None
    ) -> str:
        """Download and extract a specific file from an archive.

        Args:
            url: URL from which to download the archive, requires parseable filename.
            internal_filepath: Internal archive file path to extract, e.g. "testapp", "win32/testapp.exe";
                extracts files within an archive, not directories or multiple files.
            dest_dir: Directory in which to extract the file.
                - None (default) = binaries are automatically stored/retrieved within a cache
                - str = downloads always occur, never cached, and stored in given directory

        Returns:
            Absolute path to the cached or downloaded+extracted file

        Raises:
            RuntimeError: If the archive format is not supported or contains unsafe paths
        """
        # check cache
        if not dest_dir:
            # check for the file in the cache directory
            cached_filepath = self._retrieve_from_cache(
                url=url, filename=verified_basename(internal_filepath)
            )
            if cached_filepath:
                return cached_filepath

            # if not found, set dest_dir to the cache directory
            dest_dir = self._cache_dir_for_url(url=url)

        # create temp directory for the downloaded archive
        with TemporaryDirectory() as temp_dir:
            # get last part of the URL for the archive filename
            archive_filename = verified_basename(filepath=urlsplit(url).path)

            # construct the full path for the downloaded archive file
            # and download the archive
            archive_filepath = download_file(
                url=url, dest_filepath=os.path.join(temp_dir, archive_filename)
            )

            # extract the specific file, ensure executable, and return its path
            return ensure_executable(
                extract_file(
                    archive_filepath=archive_filepath,
                    internal_filepath=internal_filepath,
                    dest_dir=dest_dir,
                )
            )
