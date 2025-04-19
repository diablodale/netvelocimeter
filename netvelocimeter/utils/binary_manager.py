"""
Utilities for managing binary downloads and execution.
"""

import os
import platform
import stat
import tarfile
import urllib.request
import zipfile


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

def extract_file(archive_path: str, target_path: str, destination_dir: str) -> str:
    """
    Extract a specific file from an archive to a destination directory.

    Args:
        archive_path: Path to the archive file (.zip, .tgz, .tar.gz)
        target_path: Archive pathname of the file to extract
        destination_dir: Directory to extract the file into

    Returns:
        Path to the extracted file

    Raises:
        RuntimeError: If the archive format is not supported or contains unsafe paths
    """
    # modules internally use forward slashes as directory separators to comply with tar and zip archive specs
    target_path = target_path.replace('\\', '/')

    # construct the final path for the extracted file
    final_path = os.path.abspath(os.path.join(destination_dir, os.path.basename(target_path)))

    # Extract based on file extension; with safety checks not possible with shutil.unpack_archive
    if archive_path.endswith(".zip"):
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            # get info for the target file
            # module internally uses only forward slashes to comply with archive spec
            zip_info = zipf.getinfo(target_path)

            # validate it is a file with size > 0
            if zip_info.is_dir() or zip_info.file_size == 0:
                raise RuntimeError(f"File {target_path} is empty or not a file.")

            # directly extract and write to the final path
            with open(final_path, 'wb') as out_file:
                out_file.write(zipf.read(zip_info))

    elif archive_path.endswith(".tgz") or archive_path.endswith(".tar.gz"):
        # For Linux .tgz files
        with tarfile.open(archive_path, 'r:gz') as tarf:
            # get info for the target file
            # module internally uses only forward slashes to comply with archive spec
            tar_info = tarf.getmember(target_path)

            # validate it is a file with size > 0
            if not tar_info.isfile() or tar_info.size == 0:
                raise RuntimeError(f"File {target_path} is empty or not a file.")

            # custom filter that inherits from 'data' filter and flattens the path
            # to avoid directory traversal issues
            def data_flatten_filter(tarinfo: tarfile.TarInfo, dest_path: str) -> tarfile.TarInfo:
                # Flatten the file's path
                tarinfo.name = os.path.basename(tarinfo.name)

                # apply the data filter to check for absolute paths, traversal, links, devs, etc.
                tarinfo = tarfile.data_filter(tarinfo, dest_path)

                return tarinfo

            # extract with custom filter directly to final_path
            tarf.extract(tar_info, destination_dir, filter=data_flatten_filter)

    else:
        raise RuntimeError(f"Unsupported archive format: {archive_path}")

    # Ensure the extracted file exists
    if not os.path.exists(final_path):
        raise RuntimeError(f"Failed to extract {target_path} from {archive_path} to {final_path}")
    return final_path
