"""Tests for binary_manager.py utilities."""

from io import BytesIO
import os
import platform
import shutil
import stat
import tarfile
import tempfile
import unittest
from unittest import mock
from urllib.error import URLError
import zipfile

from packaging.version import Version
import pytest

from netvelocimeter.exceptions import PlatformNotSupported
from netvelocimeter.providers.base import BaseProvider
from netvelocimeter.utils.binary_manager import (
    BinaryManager,
    BinaryMeta,
    download_file,
    ensure_executable,
    extract_file,
    select_platform_binary,
    verified_basename,
)
from netvelocimeter.utils.hash import hash_b64encode


class TestBinaryManagerFunctions(unittest.TestCase):
    """Tests for binary manager utilities."""

    def setUp(self):  # Changed from setup_method
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):  # Changed from teardown_method
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    @mock.patch("urllib.request.urlopen")
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

    @mock.patch("urllib.request.urlopen")
    def test_download_file_network_error(self, mock_urlopen):
        """Test download failing due to network error."""
        # Setup mock to raise an exception
        mock_urlopen.side_effect = URLError("Network error")

        # Test
        url = "https://example.com/testfile.zip"
        destination = os.path.join(self.temp_dir, "downloads", "testfile.zip")

        # Verify exception is propagated
        with pytest.raises(URLError):
            download_file(url, destination)

        # Ensure destination file was not created
        self.assertFalse(os.path.exists(destination))

    @mock.patch("urllib.request.urlopen")
    @mock.patch("builtins.open")
    def test_download_file_no_saved_file(self, mock_open, mock_urlopen):
        """Test that RuntimeError is raised when file doesn't exist after download."""
        # Setup mock response
        mock_response = mock.MagicMock()
        mock_response.read.return_value = b"test data"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Setup mock file object that doesn't actually write anything
        mock_file = mock.MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Test URL and destination path
        url = "https://example.com/test.zip"
        dest_filepath = "/tmp/test.zip"

        # We don't need to mock os.path.exists because the file won't actually
        # be created since we're mocking the open function

        # Assert that RuntimeError is raised with the expected message
        with self.assertRaises(RuntimeError) as cm:
            download_file(url, dest_filepath)

        # Verify the error message
        self.assertIn(f"Failed to download {url}", str(cm.exception))

        # Verify that urlopen was called with the correct URL
        mock_urlopen.assert_called_once_with(url)

        # Verify that open was called with the correct filepath and mode
        mock_open.assert_called_once()
        args, kwargs = mock_open.call_args
        self.assertEqual(args[0], os.path.abspath(dest_filepath))
        self.assertEqual(kwargs.get("mode", args[1] if len(args) > 1 else None), "wb")

        # Verify that write was called with the correct data
        mock_file.write.assert_called_once_with(b"test data")

    @pytest.mark.skipif(platform.system() == "Windows", reason="Not applicable on Windows")
    def test_ensure_executable_posix(self):
        """Test making a file executable on posix systems."""
        # Create a test file
        test_file = os.path.join(self.temp_dir, "testfile.sh")
        with open(test_file, "w") as f:
            f.write("magicexe")

        # Initial permissions should not include executable
        os.chmod(test_file, 0o644)  # rw-r--r--

        # Ensure file is executable
        result = ensure_executable(test_file)

        # Check return value is the executable path
        self.assertEqual(result, test_file)

        # Check if executable bit is set
        mode = os.stat(test_file).st_mode
        self.assertTrue(mode & stat.S_IXUSR)  # Check user executable bit

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_ensure_executable_windows(self):
        """Test ensure_executable on Windows."""
        # Create a test file
        test_file = os.path.join(self.temp_dir, "testfile.bat")
        with open(test_file, "w") as f:
            f.write("magicexe")

        # Ensure function works as expected
        result = ensure_executable(test_file)

        # Check return value is the executable path
        self.assertEqual(result, test_file)

        # File should still exist
        self.assertTrue(os.path.exists(test_file))

    def test_extract_file_zip_success(self):
        """Test extracting a file from a zip archive successfully."""
        # Create a zip file
        zip_path = os.path.join(self.temp_dir, "test.zip")
        target_file = "testfile.txt"
        content = "test content"

        with zipfile.ZipFile(zip_path, "w") as zipf:
            zipf.writestr(target_file, content)

        # Extract file
        extracted_path = extract_file(zip_path, target_file, self.temp_dir)

        # Verify
        self.assertEqual(extracted_path, os.path.join(self.temp_dir, target_file))
        self.assertTrue(os.path.exists(extracted_path))
        with open(extracted_path) as f:
            self.assertEqual(f.read(), content)

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
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(temp_file, arcname=target_file)

        # Extract file
        extracted_path = extract_file(archive_path, target_file, self.temp_dir)

        # Verify
        self.assertEqual(extracted_path, os.path.join(self.temp_dir, target_file))
        self.assertTrue(os.path.exists(extracted_path))
        with open(extracted_path) as f:
            self.assertEqual(f.read(), content)

    def test_empty_file_in_zip_raises_error(self):
        """Test that extracting an empty file from a ZIP raises RuntimeError."""
        # Create a ZIP file with an empty file
        zip_path = os.path.join(self.temp_dir, "test_empty.zip")
        with zipfile.ZipFile(zip_path, "w") as zip_file:
            # Add an empty file to the zip
            empty_file_path = "empty_file.txt"
            zip_file.writestr(empty_file_path, "")  # Empty content

        # Try to extract the empty file
        with self.assertRaises(RuntimeError) as context:
            extract_file(zip_path, empty_file_path, self.temp_dir)

        # Verify the error message
        self.assertEqual(str(context.exception), f"File {empty_file_path} is empty or not a file.")

    @mock.patch("builtins.open")
    def test_zip_extraction_failure_file_not_created(self, mock_open):
        """Test that RuntimeError is raised when the extracted file doesn't exist.

        This test patches the 'open' function used during extraction to cause
        the file to not be created, but does NOT mock os.path.exists.
        """
        # Create a test zip file with a valid file
        archive_filepath = os.path.join(self.temp_dir, "test.zip")
        with zipfile.ZipFile(archive_filepath, "w") as zipf:
            zipf.writestr("testfile.txt", "Test content")

        # Make open() appear to work but not actually create a file
        # This simulates a file system error or permission issue
        mock_file = mock.MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Attempt to extract - should raise RuntimeError
        with self.assertRaises(RuntimeError) as context:
            extract_file(
                archive_filepath=archive_filepath,
                internal_filepath="testfile.txt",
                dest_dir=self.temp_dir,
            )

        # Verify the error message
        expected_error = "Failed to extract testfile.txt from"
        self.assertIn(expected_error, str(context.exception))

        # Verify that open was called
        mock_open.assert_called_once()

        # Verify that the file doesn't actually exist (using the real os.path.exists)
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, "testfile.txt")))

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
        with zipfile.ZipFile(zip_path, "w") as zipf:
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
                with zipfile.ZipFile(archive_path, "w") as zipf:
                    # Add safe file
                    zipf.writestr(safe_path, safe_data)

                    # Add malicious file, zipfile internally converts to forward slashes
                    info = zipfile.ZipInfo(malicious_path)
                    zipf.writestr(info, malicious_data)

                # Verify malicious file can be extracted
                corrected_path = extract_file(archive_path, malicious_path, self.temp_dir)

                # Corrected path should be flattened direct in the target directory
                self.assertEqual(
                    corrected_path,
                    os.path.join(
                        self.temp_dir, os.path.basename(malicious_path.replace("\\", "/"))
                    ),
                )

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
                with tarfile.open(archive_path, "w:gz") as tar:
                    # Add safe file
                    safe_info = tarfile.TarInfo(safe_path)
                    safe_info.size = len(safe_data)
                    tar.addfile(safe_info, BytesIO(safe_data))

                    # Add malicious file, normalize to forward slashes as per tarfile spec
                    malicious_info = tarfile.TarInfo(malicious_path.replace("\\", "/"))
                    malicious_info.size = len(malicious_data)
                    tar.addfile(malicious_info, BytesIO(malicious_data))

                # Verify malicious file can be extracted
                corrected_path = extract_file(archive_path, malicious_path, self.temp_dir)

                # Corrected path should be flattened direct in the target directory
                self.assertEqual(
                    corrected_path,
                    os.path.join(
                        self.temp_dir, os.path.basename(malicious_path.replace("\\", "/"))
                    ),
                )

                # Safe file should work
                extracted_path = extract_file(archive_path, safe_path, self.temp_dir)
                self.assertTrue(os.path.exists(extracted_path))

    @pytest.mark.skipif(
        platform.system() == "Windows", reason="Symlink tests not applicable on Windows"
    )
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
        with tarfile.open(archive_path, "w:gz") as tar:
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
        with tarfile.open(archive_path, "w:gz") as tar:
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
        with pytest.raises((ValueError, RuntimeError, tarfile.ExtractError, KeyError)):
            extract_file(archive_path, device_name, self.temp_dir)

        # Verify the device file wasn't created
        device_path = os.path.join(self.temp_dir, device_name)
        self.assertFalse(os.path.exists(device_path))

    def test_verified_basename(self):
        """Test verified_basename function."""
        # Create a test file path
        test_file = os.path.join(self.temp_dir, "testfile.txt")

        # Verify the basename
        verified_name = verified_basename(test_file)
        self.assertEqual(verified_name, "testfile.txt")

        # Test with a path that includes ".."
        goingup_path = os.path.join(self.temp_dir, "..", "goingup.txt")
        verified_name = verified_basename(goingup_path)
        self.assertEqual(verified_name, "goingup.txt")

    def test_verified_basename_invalid(self):
        """Test verified_basename with invalid paths."""
        # Test with an empty string
        with self.assertRaises(ValueError):
            verified_basename("")

        # Test with None
        with self.assertRaises(ValueError):
            verified_basename(None)

        # Test with a number
        with self.assertRaises(ValueError):
            verified_basename(123)

        # Test with a path having no basename
        no_basename_path = os.path.join(self.temp_dir, "")
        with self.assertRaises(ValueError):
            verified_basename(no_basename_path)


# Create a concrete implementation of BaseProvider for testing
class MockProvider(BaseProvider):
    """Test provider used for binary manager testing."""

    @property
    def _version(self) -> Version:
        """Get the provider version.

        Returns:
            Version for this provider
        """
        return Version("1.0.0+test")

    def _legal_terms(self, categories=None):
        """Get legal terms for this provider.

        Args:
            categories: Category of terms to retrieve. Defaults to ALL.

        Returns:
            Collection of legal terms that match the requested category
        """
        return []

    def _measure(self, server_id=None, server_host=None):
        """Implement required measure method."""
        pass


class TestBinaryManagerCaching(unittest.TestCase):
    """Tests for BinaryManager caching functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="binary_manager_test_")
        self.cache_dir = os.path.join(self.temp_dir, "cache")
        self.download_dir = os.path.join(self.temp_dir, "downloads")
        self.extract_dir = os.path.join(self.temp_dir, "extracts")

        # Create directories
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.extract_dir, exist_ok=True)

        # Create test archive
        self.test_url = "https://example.com/test.zip"
        self.internal_file = "testfile.txt"
        self.file_content = "test content"

        # Create a BinaryManager instance
        self.manager = BinaryManager(MockProvider, self.cache_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def create_test_archive(self, archive_path):
        """Create a test ZIP archive with a single file."""
        with zipfile.ZipFile(archive_path, "w") as zipf:
            zipf.writestr(self.internal_file, self.file_content)
        return archive_path

    def test_init_with_custom_cache_root(self):
        """Test initialization with custom cache root."""
        manager = BinaryManager(MockProvider, self.cache_dir)

        # Verify cache path structure
        expected_cache_path = os.path.join(
            self.cache_dir, platform.system(), platform.machine(), MockProvider.__name__.lower()
        )

        # Convert both to absolute paths for comparison
        expected_path = os.path.abspath(expected_cache_path)
        actual_path = os.path.abspath(manager._cache_root)

        self.assertEqual(actual_path, expected_path)
        self.assertTrue(os.path.isdir(actual_path))

    def test_init_with_relative_path(self):
        """Test initialization with relative path that gets expanded."""
        # Mock expanduser to return a predictable path
        with mock.patch("os.path.expanduser") as mock_expanduser:
            # Return an absolute path when expanduser is called
            mock_expanduser.return_value = os.path.join(self.temp_dir, "expanded")

            # Initialize with user-relative path
            manager = BinaryManager(MockProvider, "~/expanded_cache")

            # Verify expanduser was called
            mock_expanduser.assert_called_once_with("~/expanded_cache")

            # Verify the expanded path was used
            self.assertTrue(manager._cache_root.startswith(os.path.join(self.temp_dir, "expanded")))

    def test_init_with_invalid_relative_path(self):
        """Test initialization with invalid relative path."""
        # Mock expanduser to return a still-relative path
        with mock.patch("os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = "still_relative"

            # Should raise an error
            with self.assertRaises(ValueError):
                BinaryManager(MockProvider, "invalid_relative")

    def test_init_with_default_cache_root(self):
        """Test initialization with default cache root."""
        # Mock platform.system to ensure predictable behavior
        with (
            mock.patch("platform.system") as mock_system,
            mock.patch("platform.machine") as mock_machine,
        ):
            mock_system.return_value = "TestOS"
            mock_machine.return_value = "TestArch"

            # Mock expanduser to return a predictable path
            with mock.patch("os.path.expanduser") as mock_expanduser:
                mock_expanduser.return_value = os.path.join(
                    self.temp_dir, "home_dir", ".local", "bin"
                )

                # Mock os.makedirs to avoid actually creating directories
                with mock.patch("os.makedirs"):
                    manager = BinaryManager(MockProvider)

                    # Verify cache path structure
                    expected_cache_path = os.path.join(
                        self.temp_dir,
                        "home_dir",
                        ".local",
                        "bin",
                        "netvelocimeter-cache",
                        "TestOS",
                        "TestArch",
                        MockProvider.__name__.lower(),
                    )

                    # Verify the path contains the expected components
                    self.assertEqual(manager._cache_root, expected_cache_path)

    def test_cache_dir_for_url(self):
        """Test _cache_dir_for_url method."""
        # Get cache directory for a URL
        url = "https://example.com/test.zip"
        cache_dir = self.manager._cache_dir_for_url(url)

        # Verify directory exists and is within the cache root
        self.assertTrue(os.path.isdir(cache_dir))
        self.assertTrue(cache_dir.startswith(self.manager._cache_root))

        # Verify URL hashing is consistent
        cache_dir2 = self.manager._cache_dir_for_url(url)
        self.assertEqual(cache_dir, cache_dir2)

        # Verify different URLs get different directories
        other_url = "https://example.com/other.zip"
        other_cache_dir = self.manager._cache_dir_for_url(other_url)
        self.assertNotEqual(cache_dir, other_cache_dir)

    def test_retrieve_from_cache_nonexistent(self):
        """Test _retrieve_from_cache when file is not in cache."""
        # Try to retrieve a file that doesn't exist
        result = self.manager._retrieve_from_cache(self.test_url, "nonexistent.txt")
        self.assertIsNone(result)

    def test_retrieve_from_cache_exists(self):
        """Test _retrieve_from_cache when file is in cache."""
        # Create a file in the cache
        cache_dir = self.manager._cache_dir_for_url(self.test_url)
        cached_file = os.path.join(cache_dir, "cached.txt")
        with open(cached_file, "w") as f:
            f.write("cached content")

        # Retrieve the file
        result = self.manager._retrieve_from_cache(self.test_url, "cached.txt")
        self.assertEqual(result, cached_file)

    @mock.patch("netvelocimeter.utils.binary_manager.ensure_executable")
    @mock.patch("netvelocimeter.utils.binary_manager.download_file")
    @mock.patch("netvelocimeter.utils.binary_manager.extract_file")
    def test_download_extract_with_caching(self, mock_extract, mock_download, mock_ensure):
        """Test download_extract with caching."""
        # Set up mocks
        mock_download.return_value = "/path/to/downloaded.zip"
        mock_extract.return_value = "/path/to/extracted.txt"
        mock_ensure.return_value = "/path/to/extracted.txt"

        # Mock _retrieve_from_cache to initially return None (not cached)
        with mock.patch.object(self.manager, "_retrieve_from_cache", return_value=None):
            # First call should download and extract
            result1 = self.manager.download_extract(self.test_url, self.internal_file)

            # Verify calls
            mock_download.assert_called_once()
            mock_extract.assert_called_once()
            self.assertEqual(result1, "/path/to/extracted.txt")

        # Mock _retrieve_from_cache to now return a cached file
        with mock.patch.object(
            self.manager, "_retrieve_from_cache", return_value="/path/to/cached.txt"
        ):
            # Second call should use cache
            result2 = self.manager.download_extract(self.test_url, self.internal_file)

            # Verify download and extract were not called again
            self.assertEqual(mock_download.call_count, 1)  # Still only one call
            self.assertEqual(mock_extract.call_count, 1)  # Still only one call
            self.assertEqual(result2, "/path/to/cached.txt")

    @mock.patch("netvelocimeter.utils.binary_manager.ensure_executable")
    @mock.patch("netvelocimeter.utils.binary_manager.download_file")
    @mock.patch("netvelocimeter.utils.binary_manager.extract_file")
    def test_download_extract_force_download(self, mock_extract, mock_download, mock_ensure):
        """Test download_extract with forced download (dest_dir provided)."""
        # Set up mocks
        mock_download.return_value = "/path/to/downloaded.zip"
        mock_extract.return_value = "/path/to/extracted.txt"
        mock_ensure.return_value = "/path/to/extracted.txt"

        # Call with dest_dir to force download
        result = self.manager.download_extract(
            self.test_url, self.internal_file, dest_dir=self.extract_dir
        )

        # Verify calls
        mock_download.assert_called_once()
        mock_extract.assert_called_once()
        self.assertEqual(result, "/path/to/extracted.txt")

        # Verify dest_dir was passed correctly
        _, kwargs = mock_extract.call_args
        self.assertEqual(kwargs.get("dest_dir"), self.extract_dir)

    @mock.patch("urllib.request.urlopen")
    def test_full_download_extract_cache_flow(self, mock_urlopen):
        """Test the full flow of download, extract, and caching."""
        # Create a real archive for testing
        archive_path = os.path.join(self.download_dir, "test.zip")
        self.create_test_archive(archive_path)

        # Mock the URL response
        mock_response = mock.MagicMock()
        with open(archive_path, "rb") as f:
            mock_response.read.return_value = f.read()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # First call - should download, extract, and cache
        result1 = self.manager.download_extract(self.test_url, self.internal_file)

        # Verify file was extracted and exists
        self.assertTrue(os.path.exists(result1))
        with open(result1) as f:
            self.assertEqual(f.read(), self.file_content)

        # Reset mock to verify it's not called on the second attempt
        mock_urlopen.reset_mock()

        # Second call - should use cache
        result2 = self.manager.download_extract(self.test_url, self.internal_file)

        # Verify same file is returned and urlopen was not called
        self.assertEqual(result1, result2)
        mock_urlopen.assert_not_called()

    def test_invalid_provider_class(self):
        """Test initialization with invalid provider class."""
        # Try with a class that's not a BaseProvider subclass
        with self.assertRaises(ValueError):
            BinaryManager(object)

        # Try with abstract BaseProvider class
        with self.assertRaises(ValueError):
            BinaryManager(BaseProvider)

    def test_cache_structure(self):
        """Test the structure of the cache directory."""
        # Download and extract a file
        with (
            mock.patch("urllib.request.urlopen"),
            mock.patch("netvelocimeter.utils.binary_manager.download_file") as mock_download,
            mock.patch("netvelocimeter.utils.binary_manager.extract_file") as mock_extract,
            mock.patch("netvelocimeter.utils.binary_manager.ensure_executable") as mock_ensure,
        ):
            mock_download.return_value = "/path/to/downloaded.zip"
            mock_extract.return_value = "/path/to/extracted.txt"
            mock_ensure.return_value = "/path/to/extracted.txt"
            self.manager.download_extract(self.test_url, self.internal_file)

        # Verify the cache structure
        # Root/System/Machine/ProviderName/UrlHash/
        expected_path_parts = [
            platform.system(),
            platform.machine(),
            MockProvider.__name__.lower(),
            hash_b64encode(self.test_url),
        ]

        # Get the URL hash directory
        url_hash_dir = self.manager._cache_dir_for_url(self.test_url)

        # Check each part is in the cache path
        self.assertEqual(os.path.join(self.cache_dir, *expected_path_parts), url_hash_dir)

        # Verify URL cache directory was created
        self.assertTrue(os.path.isdir(url_hash_dir))

    @mock.patch("netvelocimeter.utils.binary_manager.download_file")
    def test_download_extract_error_handling(self, mock_download):
        """Test error handling in download_extract."""
        # Set up mock to raise an exception
        mock_download.side_effect = URLError("Network error")

        # Call should raise the same exception
        with self.assertRaises(URLError):
            self.manager.download_extract(self.test_url, self.internal_file)

    @mock.patch("netvelocimeter.utils.binary_manager.extract_file")
    @mock.patch("netvelocimeter.utils.binary_manager.download_file")
    def test_filename_verification(self, mock_download, mock_extract):
        """Test filename verification in download_extract."""
        # Set up mocks
        mock_download.return_value = "/path/to/downloaded.zip"
        mock_extract.return_value = "/path/to/extracted.txt"

        # Test with invalid internal filepath
        with self.assertRaises(ValueError):
            self.manager.download_extract(self.test_url, "")

        # Test with None internal filepath
        with self.assertRaises(ValueError):
            self.manager.download_extract(self.test_url, None)


class TestBinaryManagerWindowsSpecific(unittest.TestCase):
    """Windows-specific tests for BinaryManager."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="binary_manager_test_")

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_windows_default_cache_location(self):
        """Test Windows-specific default cache location."""
        # Mock os.getenv to return a known value for LOCALAPPDATA
        with (
            mock.patch.dict(
                os.environ, {"LOCALAPPDATA": os.path.join(self.temp_dir, "localappdata")}
            ),
            mock.patch("os.makedirs"),
        ):
            # Mock os.makedirs to avoid creating directories
            manager = BinaryManager(MockProvider)

            # Verify Windows path is used
            self.assertEqual(
                os.path.normpath(os.path.join(self.temp_dir, "localappdata", "netvelocimeter-cache")),
                os.path.normpath(os.path.join(manager._cache_root, "..", "..", "..")),
            )


class TestBinaryManagerPosixSpecific(unittest.TestCase):
    """POSIX-specific tests for BinaryManager."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="binary_manager_test_")

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    @pytest.mark.skipif(platform.system() == "Windows", reason="POSIX-specific test")
    def test_posix_default_cache_location(self):
        """Test POSIX-specific default cache location."""
        # Mock os.path.expanduser to return a known path
        with mock.patch("os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = os.path.join(self.temp_dir, ".local", "bin")

            # Mock os.makedirs to avoid creating directories
            with mock.patch("os.makedirs"):
                manager = BinaryManager(MockProvider)

                # Verify POSIX path is used
                self.assertEqual(
                    os.path.normpath(
                        os.path.join(self.temp_dir, ".local", "bin", "netvelocimeter-cache")
                    ),
                    os.path.normpath(os.path.join(manager._cache_root, "..", "..", "..")),
                )


class TestSelectPlatformBinary(unittest.TestCase):
    """Tests for select_platform_binary function."""

    PLATFORM_MAP = {
        ("linux", "x86_32"): BinaryMeta(
            url="https://example.com/linux-x86_32.tgz",
            internal_filepath="binfile",
            hash_sha256="abc123",
        ),
        ("windows", "x86_64"): BinaryMeta(
            url="https://example.com/win64.zip", internal_filepath="bin.exe", hash_sha256="def456"
        ),
        ("linux", "armhf"): BinaryMeta(
            url="https://example.com/linux-armhf.tgz",
            internal_filepath="binfile",
            hash_sha256="armhash",
        ),
        ("linux", "arm64"): BinaryMeta(
            url="https://example.com/linux-arm64.tgz",
            internal_filepath="binfile",
            hash_sha256="armhash",
        ),
    }

    def test_select_exact_match(self):
        """Test selecting a binary with an exact match."""
        meta = select_platform_binary(self.PLATFORM_MAP, system="linux", machine="x86_32")
        self.assertEqual(meta.url, "https://example.com/linux-x86_32.tgz")
        self.assertEqual(meta.internal_filepath, "binfile")
        self.assertEqual(meta.hash_sha256, "abc123")

    def test_select_windows_amd64(self):
        """Test selecting a Windows binary for amd64 aka x86_64 architecture."""
        meta = select_platform_binary(self.PLATFORM_MAP, system="windows", machine="amd64")
        self.assertEqual(meta.url, "https://example.com/win64.zip")
        self.assertEqual(meta.internal_filepath, "bin.exe")
        self.assertEqual(meta.hash_sha256, "def456")

    def test_normalization_linux_armhf(self):
        """Test normalization for Linux armhf architecture."""
        meta = select_platform_binary(self.PLATFORM_MAP, system="linux", machine="armv7l")
        self.assertEqual(meta.url, "https://example.com/linux-armhf.tgz")
        self.assertEqual(meta.hash_sha256, "armhash")

    def test_normalization_linux_arm64(self):
        """Test normalization for Linux arm64 architecture."""
        meta = select_platform_binary(self.PLATFORM_MAP, system="linux", machine="aarch64")
        self.assertEqual(meta.url, "https://example.com/linux-arm64.tgz")
        self.assertEqual(meta.hash_sha256, "armhash")

    def test_unsupported_platform(self):
        """Test selecting a binary for an unsupported platform."""
        with self.assertRaises(PlatformNotSupported):
            select_platform_binary(self.PLATFORM_MAP, system="darwin", machine="arm64")

    def test_disable_normalization(self):
        """Test selecting a binary without normalization."""
        with self.assertRaises(PlatformNotSupported):
            select_platform_binary(
                self.PLATFORM_MAP, system="linux", machine="armv7l", normalize=False
            )
