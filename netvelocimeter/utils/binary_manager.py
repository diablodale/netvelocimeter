"""
Utilities for managing binary downloads and execution.
"""

import os
import stat
import platform
import urllib.request

def download_file(url: str, destination: str) -> None:
    """
    Download a file from a URL to a local destination.

    Args:
        url: URL to download from.
        destination: Local path to save the file.
    """
    absolute_destination = os.path.abspath(destination)
    os.makedirs(os.path.dirname(absolute_destination), exist_ok=True)

    with urllib.request.urlopen(url) as response:
        with open(absolute_destination, 'wb') as out_file:
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

def extract_file(archive_path: str, target_file: str, destination_dir: str) -> str:
    """
    Extract a specific file from an archive to a destination directory.

    Args:
        archive_path: Path to the archive file (.zip, .tgz, .tar.gz)
        target_file: Name of the file to extract
        destination_dir: Directory to extract the file to

    Returns:
        Path to the extracted file

    Raises:
        RuntimeError: If the archive format is not supported or contains unsafe paths
    """
    extracted_path = os.path.join(destination_dir, target_file)

    # Extract based on file extension
    if archive_path.endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            # Check for path traversal attempts
            zip_info = zip_ref.getinfo(target_file)
            if zip_info.filename != target_file or '..' in zip_info.filename or zip_info.filename.startswith('/'):
                raise RuntimeError(f"Potentially unsafe file in archive: {zip_info.filename}")
            zip_ref.extract(target_file, destination_dir)
    elif archive_path.endswith(".tgz") or archive_path.endswith(".tar.gz"):
        # For Linux .tgz files
        import tarfile
        with tarfile.open(archive_path, 'r:gz') as tar:
            # data filter checks for path traversal, links, devs, etc.
            tar.extract(target_file, destination_dir, filter="data")
    else:
        raise RuntimeError(f"Unsupported archive format: {archive_path}")

    return extracted_path
