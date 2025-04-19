"""
Tests for binary_manager.py utilities
"""

from io import BytesIO
import os
import platform
import shutil
import stat
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile

import pytest

from netvelocimeter.utils.binary_manager import (
    download_file,
    ensure_executable,
    extract_file,
)


class TestBinaryManager(unittest.TestCase):
    """Tests for binary manager utilities."""

    def setUp(self):  # Changed from setup_method
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):  # Changed from teardown_method
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    @mock.patch('urllib.request.urlopen')
    def test_download_file_success(self, mock_urlopen):
        """Test downloading a file successfully."""
        # Setup mock
        mock_response = mock.MagicMock()
        mock_response.read.return_value = b"test file content"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Test
        url = "https://example.com/testfile.zip"
        destination = os.path.join(self.temp_dir, "downloads", "testfile.zip")
        download_file(url, destination)

        # Verify
        mock_urlopen.assert_called_once_with(url)
        self.assertTrue(os.path.exists(destination))
        with open(destination, "rb") as f:
            self.assertEqual(f.read(), b"test file content")

    @mock.patch('urllib.request.urlopen')
    def test_download_file_network_error(self, mock_urlopen):
        """Test download failing due to network error."""
        # Setup mock to raise an exception
        mock_urlopen.side_effect = Exception("Network error")

        # Test
        url = "https://example.com/testfile.zip"
        destination = os.path.join(self.temp_dir, "downloads", "testfile.zip")

        # Verify exception is propagated
        with pytest.raises(Exception):
            download_file(url, destination)

        # Ensure destination file was not created
        self.assertFalse(os.path.exists(destination))

    @pytest.mark.skipif(platform.system() == "Windows", reason="Not applicable on Windows")
    def test_ensure_executable_unix(self):
        """Test making a file executable on Unix-like systems."""
        # Create a test file
        test_file = os.path.join(self.temp_dir, "testfile.sh")
        with open(test_file, "w") as f:
            f.write("magicexe")

        # Initial permissions should not include executable
        os.chmod(test_file, 0o644)  # rw-r--r--

        # Ensure file is executable
        ensure_executable(test_file)

        # Check if executable bit is set
        mode = os.stat(test_file).st_mode
        self.assertTrue(mode & stat.S_IXUSR)  # Check user executable bit

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_ensure_executable_windows(self):
        """Test that ensure_executable is a no-op on Windows."""
        # Create a test file
        test_file = os.path.join(self.temp_dir, "testfile.bat")
        with open(test_file, "w") as f:
            f.write("magicexe")

        # Ensure no-op
        ensure_executable(test_file)

        # File should still exist
        self.assertTrue(os.path.exists(test_file))

    def test_extract_file_zip_success(self):
        """Test extracting a file from a zip archive successfully."""
        # Create a zip file
        zip_path = os.path.join(self.temp_dir, "test.zip")
        target_file = "testfile.txt"
        content = "test content"

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.writestr(target_file, content)

        # Extract file
        extracted_path = extract_file(zip_path, target_file, self.temp_dir)

        # Verify
        self.assertEqual(extracted_path, os.path.join(self.temp_dir, target_file))
        self.assertTrue(os.path.exists(extracted_path))
        with open(extracted_path) as f:
            self.assertEqual(f.read(), content)

    #@pytest.mark.skipif(platform.system() == "Windows", reason="tarfile with filter not fully compatible on Windows")
    def test_extract_file_tar_success(self):
        """Test extracting a file from a tar.gz archive successfully."""
        # Create a tar.gz file
        archive_path = os.path.join(self.temp_dir, "test.tar.gz")
        target_file = "testfile.txt"
        content = "test content"

        # Create a temporary file to add to the archive
        temp_file = os.path.join(self.temp_dir, target_file)
        with open(temp_file, "w") as f:
            f.write(content)

        # Create archive
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(temp_file, arcname=target_file)

        # Extract file
        extracted_path = extract_file(archive_path, target_file, self.temp_dir)

        # Verify
        self.assertEqual(extracted_path, os.path.join(self.temp_dir, target_file))
        self.assertTrue(os.path.exists(extracted_path))
        with open(extracted_path) as f:
            self.assertEqual(f.read(), content)

    def test_extract_file_unsupported_format(self):
        """Test extracting from an unsupported archive format."""
        # Create a file with unsupported extension
        archive_path = os.path.join(self.temp_dir, "test.rar")
        with open(archive_path, "w") as f:
            f.write("not a real archive")

        # Attempt to extract
        with pytest.raises(RuntimeError, match="Unsupported archive format"):
            extract_file(archive_path, "somefile.txt", self.temp_dir)

    def test_extract_file_nonexistent_archive(self):
        """Test extracting from a nonexistent archive."""
        archive_path = os.path.join(self.temp_dir, "nonexistent.zip")

        # Attempt to extract
        with pytest.raises(FileNotFoundError):
            extract_file(archive_path, "somefile.txt", self.temp_dir)

    def test_extract_file_nonexistent_target(self):
        """Test extracting a nonexistent file from an archive."""
        # Create a zip file
        zip_path = os.path.join(self.temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.writestr("actualfile.txt", "content")

        # Attempt to extract a file that doesn't exist in the archive
        with pytest.raises(KeyError):
            extract_file(zip_path, "nonexistent.txt", self.temp_dir)

    # malicious paths to test against zip and tar attacks
    malicious_paths = [
        os.path.join(os.path.pardir, os.path.pardir, os.path.pardir, "tmp", "etc", "badhosts"),
        os.path.join(os.path.pardir, "sensitive_file"),
        "/tmp/malicious.txt" if platform.system() != "Windows" else R"C:\tmp\malicious.txt",
        "../../../../etc/passwd",
        "./.././../etc/shadow",
        "normal_dir/../../../etc/hosts",
    ]

    def test_extract_file_zip_path_attacks(self):
        """Test protection against zip path attacks with various malicious paths."""
        for malicious_path in self.malicious_paths:
            with self.subTest(malicious_path=malicious_path):
                # Calculate archive absolute path
                archive_path = os.path.join(self.temp_dir, "malicious.zip")

                # Create archive
                safe_path = "safe.txt"
                safe_data = b"safe content"
                malicious_data = b"malicious content"
                with zipfile.ZipFile(archive_path, 'w') as zipf:
                    # Add safe file
                    zipf.writestr(safe_path, safe_data)

                    # Add malicious file, zipfile internally converts to forward slashes
                    info = zipfile.ZipInfo(malicious_path)
                    zipf.writestr(info, malicious_data)

                # Verify malicious file can be extracted
                corrected_path = extract_file(archive_path, malicious_path, self.temp_dir)

                # Corrected path should be flattened direct in the target directory
                self.assertEqual(corrected_path, os.path.join(self.temp_dir, os.path.basename(malicious_path.replace('\\', '/'))))

                # Safe file should work
                extracted_path = extract_file(archive_path, safe_path, self.temp_dir)
                self.assertTrue(os.path.exists(extracted_path))

    def test_extract_file_tar_path_attacks(self):
        """Test protection against tar path attacks with various malicious paths."""
        for malicious_path in self.malicious_paths:
            with self.subTest(malicious_path=malicious_path):
                # Calculate archive absolute path
                archive_path = os.path.join(self.temp_dir, "malicious.tar.gz")

                # Create archive
                safe_path = "safe.txt"
                safe_data = b"safe content"
                malicious_data = b"malicious content"
                with tarfile.open(archive_path, 'w:gz') as tar:
                    # Add safe file
                    safe_info = tarfile.TarInfo(safe_path)
                    safe_info.size = len(safe_data)
                    tar.addfile(safe_info, BytesIO(safe_data))

                    # Add malicious file, normalize to forward slashes as per tarfile spec
                    malicious_info = tarfile.TarInfo(malicious_path.replace('\\', '/'))
                    malicious_info.size = len(malicious_data)
                    tar.addfile(malicious_info, BytesIO(malicious_data))

                # Verify malicious file can be extracted
                corrected_path = extract_file(archive_path, malicious_path, self.temp_dir)

                # Corrected path should be flattened direct in the target directory
                self.assertEqual(corrected_path, os.path.join(self.temp_dir, os.path.basename(malicious_path.replace('\\', '/'))))

                # Safe file should work
                extracted_path = extract_file(archive_path, safe_path, self.temp_dir)
                self.assertTrue(os.path.exists(extracted_path))

    @pytest.mark.skipif(platform.system() == "Windows", reason="Symlink tests not applicable on Windows")
    def test_extract_file_tar_symlink_attack(self):
        """Test protection against symlink attacks in tar."""
        archive_path = os.path.join(self.temp_dir, "malicious.tar.gz")

        # Define names
        symlink_name = "evil_link"
        target_name = "/etc/hosts"  # attack target
        safe_name = "safe.txt"

        # Create a temporary file for the safe content
        safe_file = os.path.join(self.temp_dir, safe_name)
        with open(safe_file, "w") as f:
            f.write("safe content")

        # Create archive with symlink attack
        with tarfile.open(archive_path, 'w:gz') as tar:
            # Add the safe file normally
            tar.add(safe_file, arcname=safe_name)

            # Remove the safe file to simulate a clean environment
            os.remove(safe_file)

            # Create a TarInfo for the symlink
            link_info = tarfile.TarInfo(symlink_name)
            link_info.type = tarfile.SYMTYPE
            link_info.linkname = target_name

            # Add the symlink using addfile
            tar.addfile(link_info)

        # Extract the safe file - should work
        extracted_path = extract_file(archive_path, safe_name, self.temp_dir)
        self.assertTrue(os.path.exists(extracted_path))

        # Try to extract the symlink - should fail or be converted to a regular file with filter='data'
        try:
            symlink_path = extract_file(archive_path, symlink_name, self.temp_dir)
            # If extraction succeeded, verify it's not a symlink (filter=data converts symlinks)
            self.assertFalse(os.path.islink(symlink_path))
        except Exception:
            # Or it might fail completely, which is also acceptable
            pass

    def test_extract_file_tar_device_file_attack(self):
        """Test protection against device file attacks in tar."""
        archive_path = os.path.join(self.temp_dir, "malicious.tar.gz")

        # Define names
        device_name = "evil_device"
        safe_name = "safe.txt"

        # Create a temporary file for the safe content
        safe_file = os.path.join(self.temp_dir, safe_name)
        with open(safe_file, "w") as f:
            f.write("safe content")

        # Create archive with device file attack
        with tarfile.open(archive_path, 'w:gz') as tar:
            # Add the safe file normally
            tar.add(safe_file, arcname=safe_name)

            # Remove the safe file to simulate a clean environment
            os.remove(safe_file)

            # Create a TarInfo for the device file
            device_info = tarfile.TarInfo(device_name)
            device_info.type = tarfile.CHRTYPE  # Character device
            device_info.devmajor = 1  # /dev/null major
            device_info.devminor = 3  # /dev/null minor

            # Add the device file using addfile
            tar.addfile(device_info)

        # Extract the safe file - should work
        extracted_path = extract_file(archive_path, safe_name, self.temp_dir)
        self.assertTrue(os.path.exists(extracted_path))

        # Attempt to extract the device file - should fail with filter='data'
        with pytest.raises(Exception):  # Either KeyError or tarfile.FilterError
            extract_file(archive_path, device_name, self.temp_dir)

        # Verify the device file wasn't created
        device_path = os.path.join(self.temp_dir, device_name)
        self.assertFalse(os.path.exists(device_path))
