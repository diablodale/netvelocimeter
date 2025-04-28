"""Tests for the Ookla provider."""

from datetime import timedelta
from io import BytesIO
import json
import os
import platform
import shutil
import tarfile
import tempfile
import unittest
from unittest import mock
from urllib.error import URLError
from urllib.request import pathname2url

from packaging.version import InvalidVersion, Version
import pytest

from netvelocimeter.exceptions import PlatformNotSupported
from netvelocimeter.providers.base import ServerInfo
from netvelocimeter.providers.ookla import OoklaProvider
from netvelocimeter.terms import LegalTermsCategory
from netvelocimeter.utils.binary_manager import BinaryManager


class TestOoklaProvider(unittest.TestCase):
    """Test Ookla provider implementation."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for the tests
        self.temp_dir = tempfile.mkdtemp()
        self.archive_path = os.path.join(self.temp_dir, "simulate_internet", "linux.tgz")
        os.makedirs(os.path.dirname(self.archive_path), exist_ok=True)
        self.archive_url = f"file:{pathname2url(self.archive_path)}"

        # Create archive
        internal_path = "speedtest.exe" if platform.system().lower() == "windows" else "speedtest"
        file_data = b"This is a test binary"
        with tarfile.open(self.archive_path, "w:gz") as tar:
            info = tarfile.TarInfo(internal_path)
            info.size = len(file_data)
            info.mode = 0o755
            tar.addfile(info, BytesIO(file_data))

        # More robust patching
        self.patchers = []

        # Patch OoklaProvider _download_url to return self.archive_url
        patcher = mock.patch.object(OoklaProvider, "_download_url", return_value=self.archive_url)
        patcher.start()
        self.patchers.append(patcher)

        # Patch _parse_version to return a Version object
        patcher = mock.patch.object(OoklaProvider, "_parse_version", return_value=Version("1.0.0"))
        patcher.start()
        self.patchers.append(patcher)

        # With these patches in place, now create the provider
        self.provider = OoklaProvider(self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        # Stop all patches
        for patcher in self.patchers:
            patcher.stop()

        shutil.rmtree(self.temp_dir)

    def test_legal_requirements(self):
        """Test Ookla legal terms."""
        # Get legal terms using the API
        terms = self.provider.legal_terms()

        # Verify we have terms
        self.assertTrue(terms)  # Collection should not be empty

        # Find EULA terms
        eula_terms = [term for term in terms if term.category == LegalTermsCategory.EULA]
        self.assertTrue(eula_terms, "No EULA terms found")
        self.assertIsNotNone(eula_terms[0].text)
        self.assertEqual(eula_terms[0].url, "https://www.speedtest.net/about/eula")

        # Find privacy terms
        privacy_terms = [term for term in terms if term.category == LegalTermsCategory.PRIVACY]
        self.assertTrue(privacy_terms, "No privacy terms found")
        self.assertIsNotNone(privacy_terms[0].text)
        self.assertEqual(privacy_terms[0].url, "https://www.speedtest.net/about/privacy")

        # Find service terms
        service_terms = [term for term in terms if term.category == LegalTermsCategory.SERVICE]
        self.assertTrue(service_terms, "No service terms found")
        self.assertIsNotNone(service_terms[0].text)
        self.assertEqual(service_terms[0].url, "https://www.speedtest.net/about/terms")

        # Test acceptance tracking api inherited from BaseProvider
        self.assertFalse(self.provider.has_accepted_terms())

        # Accept terms with api inherited from BaseProvider
        self.provider.accept_terms(terms)

        # Verify acceptance was recorded with api inherited from BaseProvider
        self.assertTrue(self.provider.has_accepted_terms())

    @mock.patch("subprocess.run")
    def test_run_speedtest_error_not_terms_acceptance(self, mock_run):
        """Test running speedtest without acceptance."""
        # Mock subprocess to simulate error when license not accepted
        mock_process = mock.Mock()
        mock_process.returncode = 1
        mock_process.stderr = "Simulated app error: something is wrong"
        mock_run.return_value = mock_process

        # Do NOT accept any terms
        self.assertFalse(self.provider.has_accepted_terms())

        # Verify low-level provider exception is raised due to subprocess.run and not legal terms
        with self.assertRaises(RuntimeError) as context:
            self.provider._run_speedtest()

        self.assertIn("Simulated app error", str(context.exception))

    @mock.patch("subprocess.run")
    def test_run_speedtest_terms_flags(self, mock_run):
        """Test running speedtest with legal terms flags."""
        # Mock successful subprocess run
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps(
            {
                "download": {"bandwidth": 12500000},  # 100 Mbps
                "upload": {"bandwidth": 2500000},  # 20 Mbps
                "ping": {"latency": 15.5, "jitter": 3.2},
                "server": {"id": "1234", "name": "Test Server"},
            }
        )
        mock_run.return_value = mock_process

        result = self.provider._run_speedtest()

        # Verify --accept-license and --accept-gdpr flags were included
        args, kwargs = mock_run.call_args
        cmd_line = args[0]
        self.assertIn("--accept-license", cmd_line)
        self.assertIn("--accept-gdpr", cmd_line)

        # Verify result parsing
        self.assertEqual(result["download"]["bandwidth"], 12500000)

    @mock.patch("subprocess.run")
    def test_get_servers(self, mock_run):
        """Test getting server list."""
        # Mock server list response
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps(
            {
                "servers": [
                    {
                        "name": "Server 1",
                        "id": "1",
                        "location": "Location 1",
                        "country": "Country 1",
                        "host": "server1.example.com",
                    },
                    {
                        "name": "Server 2",
                        "location": "Location 2",
                        "country": "Country 2",
                        "host": "server2.example.com",
                    },
                ]
            }
        )
        mock_run.return_value = mock_process

        # verify has not accepted terms
        self.assertFalse(self.provider.has_accepted_terms())

        # should run without accepting terms because provider-level apis do not enforce
        servers = self.provider.servers

        # Verify --servers flag was included
        args, _kwargs = mock_run.call_args
        cmd_line = args[0]
        self.assertIn("--servers", cmd_line)

        # Update assertions to account for optional id:
        for server in servers:
            self.assertIsInstance(server, ServerInfo)
            self.assertIsInstance(server.name, str)
            # Don't assume id is required - it may be None
            if server.id is not None:
                self.assertTrue(isinstance(server.id, (str, int)))

        # Verify server list parsing
        self.assertEqual(len(servers), 2)
        self.assertEqual(servers[0].id, "1")
        self.assertEqual(servers[0].name, "Server 1")
        self.assertEqual(servers[0].host, "server1.example.com")
        self.assertEqual(servers[1].name, "Server 2")
        self.assertEqual(servers[1].country, "Country 2")

    @mock.patch("subprocess.run")
    def test_measure_with_server_id(self, mock_run):
        """Test measurement with specified server ID."""
        # Mock successful measurement
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps(
            {
                "download": {"bandwidth": 12500000, "latency": {"iqm": 42.985}},
                "upload": {"bandwidth": 2500000, "latency": {"iqm": 178.546}},
                "ping": {"latency": 15.5, "jitter": 3.2},
                "server": {"id": "1234", "name": "Test Server"},
            }
        )
        mock_run.return_value = mock_process

        result = self.provider.measure(server_id=1234)

        # Verify timedelta conversion
        self.assertIsInstance(result.ping_latency, timedelta)
        self.assertIsInstance(result.ping_jitter, timedelta)
        self.assertAlmostEqual(result.ping_latency.total_seconds() * 1000, 15.5)
        self.assertAlmostEqual(result.ping_jitter.total_seconds() * 1000, 3.2)

        # Verify --server-id flag was included
        args, kwargs = mock_run.call_args
        cmd_line = args[0]
        self.assertIn("--server-id", cmd_line)
        self.assertIn("1234", cmd_line)

    @mock.patch("subprocess.run")
    def test_measure_with_server_host(self, mock_run):
        """Test measurement with specified server host."""
        # Mock successful measurement
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps(
            {
                "download": {"bandwidth": 12500000, "latency": {"iqm": 42.985}},
                "upload": {"bandwidth": 2500000, "latency": {"iqm": 178.546}},
                "ping": {"latency": 15.5, "jitter": 3.2},
                "server": {"id": "1234", "name": "Test Server"},
            }
        )
        mock_run.return_value = mock_process

        result = self.provider.measure(server_host="example.com")

        # Verify timedelta conversion
        self.assertIsInstance(result.ping_latency, timedelta)
        self.assertIsInstance(result.ping_jitter, timedelta)

        # Verify --host flag was included
        args, kwargs = mock_run.call_args
        cmd_line = args[0]
        self.assertIn("--host", cmd_line)
        self.assertIn("example.com", cmd_line)

    def test_parse_version(self):
        """Test getting provider version."""
        # Version is already mocked in setUp
        version = self.provider.version
        self.assertEqual(version, Version("1.0.0"))

    def test_measure_with_sample_data(self):
        """Test measurement using sample data from JSON file."""
        # Path to sample data file
        sample_path = os.path.join(os.path.dirname(__file__), "samples", "ookla.json")

        # Load sample data
        with open(sample_path) as f:
            sample_data = json.load(f)

        # Mock subprocess.run to return our sample data
        with mock.patch("subprocess.run") as mock_run:
            mock_process = mock.Mock()
            mock_process.returncode = 0
            mock_process.stdout = json.dumps(sample_data)
            mock_run.return_value = mock_process

            # Run measurement
            result = self.provider.measure()

            # Verify subprocess was called correctly
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd_line = args[0]
            self.assertIn("--accept-license", cmd_line)
            self.assertIn("--accept-gdpr", cmd_line)

            # Verify download speed (bandwidth in bits/sec converted to Mbps)
            # 13038400 bytes/s * 8 bits/byte / 1,000,000 bits/Mbps = 104.3072 Mbps
            self.assertAlmostEqual(result.download_speed, 104.3072, places=4)

            # Verify upload speed
            # 4771435 bytes/s * 8 bits/byte / 1,000,000 bits/Mbps = 38.17148 Mbps
            self.assertAlmostEqual(result.upload_speed, 38.17148, places=4)

            # Verify ping metrics
            self.assertIsInstance(result.ping_latency, timedelta)
            self.assertIsInstance(result.ping_jitter, timedelta)
            self.assertAlmostEqual(result.ping_latency.total_seconds() * 1000, 10.055, places=3)
            self.assertAlmostEqual(result.ping_jitter.total_seconds() * 1000, 3.475, places=3)

            # Verify latency metrics
            self.assertIsInstance(result.download_latency, timedelta)
            self.assertIsInstance(result.upload_latency, timedelta)
            self.assertAlmostEqual(result.download_latency.total_seconds() * 1000, 42.985, places=3)
            self.assertAlmostEqual(result.upload_latency.total_seconds() * 1000, 178.546, places=3)

            # Verify packet loss
            self.assertEqual(result.packet_loss, 0)

            # Verify server info
            self.assertIsNotNone(result.server_info)
            self.assertEqual(result.server_info.id, 20507)
            self.assertEqual(result.server_info.name, "DNS:NET Internet Service GmbH")
            self.assertEqual(result.server_info.location, "Berlin")
            self.assertEqual(result.server_info.country, "Germany")
            self.assertEqual(result.server_info.host, "speedtest01.dns-net.de")

            # Verify raw result was stored
            self.assertEqual(result.raw_result, sample_data)

            # Update verification for the persist URL
            self.assertEqual(
                result.persist_url,
                "https://www.speedtest.net/result/c/c37d62b5-52ab-5252-bc06-db205451a1e5",
            )

            # Update verification for the measurement ID
            self.assertEqual(result.id, "c37d62b5-52ab-5252-bc06-db205451a1e5")

            # Update assertions if verifying server_info:
            self.assertEqual(result.server_info.name, "DNS:NET Internet Service GmbH")

            self.assertEqual(result.server_info.id, 20507)

    @mock.patch("subprocess.run")
    def test_measure_without_persist_url(self, mock_run):
        """Test measurement without a persist URL in the result."""
        # Mock response without the result.url field
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps(
            {
                "download": {"bandwidth": 12500000, "latency": {"iqm": 42.985}},
                "upload": {"bandwidth": 2500000, "latency": {"iqm": 178.546}},
                "ping": {"latency": 15.5, "jitter": 3.2},
                "server": {"id": "1234", "name": "Test Server"},
            }
        )
        mock_run.return_value = mock_process

        result = self.provider.measure()

        # The persist_url should be None
        self.assertIsNone(result.persist_url)

    @mock.patch("subprocess.run")
    def test_measure_without_result_id(self, mock_run):
        """Test measurement without a result ID in the response."""
        # Mock response without the result.id field
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps(
            {
                "download": {"bandwidth": 12500000, "latency": {"iqm": 42.985}},
                "upload": {"bandwidth": 2500000, "latency": {"iqm": 178.546}},
                "ping": {"latency": 15.5, "jitter": 3.2},
                "server": {"id": "1234", "name": "Test Server"},
            }
        )
        mock_run.return_value = mock_process

        result = self.provider.measure()

        # The id should be None
        self.assertIsNone(result.id)

    @mock.patch("subprocess.run")
    def test_measure_download(self, mock_run):
        """Test download speed calculation."""
        # Mock with different bandwidth values
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps(
            {
                "download": {"bandwidth": 10000000, "latency": {"iqm": 42.985}},  # 80 Mbps
                "upload": {"bandwidth": 2500000, "latency": {"iqm": 178.546}},
                "ping": {"latency": 15.5, "jitter": 3.2},
                "server": {"id": "1234", "name": "Test Server"},
            }
        )
        mock_run.return_value = mock_process

        result = self.provider.measure()

        # 10000000 bytes/s * 8 bits/byte / 1,000,000 bits/Mbps = 80 Mbps
        self.assertAlmostEqual(result.download_speed, 80.0, places=2)

    @mock.patch("subprocess.run")
    def test_measure_upload(self, mock_run):
        """Test upload speed calculation."""
        # Mock with different bandwidth values
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps(
            {
                "download": {"bandwidth": 12500000, "latency": {"iqm": 42.985}},
                "upload": {"bandwidth": 5000000, "latency": {"iqm": 178.546}},  # 40 Mbps
                "ping": {"latency": 15.5, "jitter": 3.2},
                "server": {"id": "1234", "name": "Test Server"},
            }
        )
        mock_run.return_value = mock_process

        result = self.provider.measure()

        # 5000000 bytes/s * 8 bits/byte / 1,000,000 bits/Mbps = 40 Mbps
        self.assertAlmostEqual(result.upload_speed, 40.0, places=2)

    @mock.patch("subprocess.run")
    def test_measure_latency(self, mock_run):
        """Test latency handling."""
        # Mock with different latency values
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps(
            {
                "download": {"bandwidth": 12500000, "latency": {"iqm": 100.5}},  # 100.5ms
                "upload": {"bandwidth": 2500000, "latency": {"iqm": 200.75}},  # 200.75ms
                "ping": {"latency": 50.25, "jitter": 10.5},  # 50.25ms, 10.5ms
                "server": {"id": "1234", "name": "Test Server"},
            }
        )
        mock_run.return_value = mock_process

        result = self.provider.measure()

        self.assertAlmostEqual(result.download_latency.total_seconds() * 1000, 100.5, places=2)
        self.assertAlmostEqual(result.upload_latency.total_seconds() * 1000, 200.75, places=2)
        self.assertAlmostEqual(result.ping_latency.total_seconds() * 1000, 50.25, places=2)
        self.assertAlmostEqual(result.ping_jitter.total_seconds() * 1000, 10.5, places=2)


class TestOoklaProviderVersionParsing(unittest.TestCase):
    """Separate test class for version parsing functionality."""

    def test_invalid_version_format(self):
        """Test handling of invalid version format."""
        with mock.patch("subprocess.run") as mock_run:
            # Set up mock for invalid version output
            mock_process = mock.Mock()
            mock_process.returncode = 0
            mock_process.stdout = "Something invalid"
            mock_run.return_value = mock_process

            # Need to patch the download_extract method to avoid actual downloads
            with mock.patch.object(
                BinaryManager, "download_extract", return_value="/path/to/speedtest"
            ):
                # Create a new provider instance
                # This should call _parse_version with our mocked subprocess.run and raise an error
                with self.assertRaises(InvalidVersion):
                    _ = OoklaProvider("/temp/dir")

                # Verify subprocess was called
                mock_run.assert_called_once()

    def test_valid_version_format(self):
        """Test handling of valid version format."""
        with (
            mock.patch("subprocess.run") as mock_run,
            mock.patch.object(
                BinaryManager, "download_extract", return_value="speedtest_path_1234"
            ),
        ):
            # Set up mock for valid version output
            mock_process = mock.Mock()
            mock_process.returncode = 0
            mock_process.stdout = (
                "Speedtest by Ookla 1.2.0.84 (ea6b6773cf) "
                "Linux/x86_64-linux-musl "
                "5.15.167.4-microsoft-standard-WSL2 x86_64"
            )
            mock_run.return_value = mock_process

            # Create a clean provider instance
            provider = OoklaProvider("/temp/dir")

            # Version should be parsed correctly
            self.assertEqual(provider.version, Version("1.2.0.84+ea6b6773cf"))

            # Verify subprocess call
            mock_run.assert_called_once_with(
                [
                    "speedtest_path_1234",
                    "--progress=no",
                    "--accept-license",
                    "--accept-gdpr",
                    "--version",
                ],
                capture_output=True,
                text=True,
            )

    def test_parse_version_invalid_format(self):
        """Test handling completely different format than expected."""
        with mock.patch("subprocess.run") as mock_run:
            mock_process = mock.Mock()
            mock_process.returncode = 0
            # Test with completely different format than expected
            mock_process.stdout = "Version: ABC123"
            mock_run.return_value = mock_process

            with (
                mock.patch.object(BinaryManager, "download_extract", return_value="speedtest_path"),
                self.assertRaises(InvalidVersion),
            ):
                _ = OoklaProvider("/temp/dir")


class TestOoklaProviderPlatformDetection(unittest.TestCase):
    """Test platform detection for OoklaProvider."""

    def setUp(self):
        """Set up a clean test directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.temp_dir)

    @mock.patch("platform.system")
    @mock.patch("platform.machine")
    def test_platform_detection_mapping(self, mock_machine, mock_system):
        """Test platform and architecture mapping logic."""
        # Test ARM mapping on Linux
        mock_system.return_value = "Linux"
        mock_machine.return_value = "armv7l"

        # Save the original method to avoid recursion
        original_download_url = OoklaProvider._download_url

        # We need to patch binary manager methods
        with (
            mock.patch.object(
                BinaryManager, "download_extract", return_value="/mock/path/speedtest"
            ),
            mock.patch.object(OoklaProvider, "_parse_version", return_value=Version("1.0.0")),
        ):
            # Create the provider
            provider = OoklaProvider(self.temp_dir)

            # Verify the binary path and version
            self.assertEqual(provider._BINARY_PATH, "/mock/path/speedtest")
            self.assertEqual(provider.version, Version("1.0.0"))

            # After creation, call the original method to get the URL that would be used
            # This avoids the recursion issue
            with mock.patch.object(
                OoklaProvider, "_download_url", side_effect=original_download_url
            ):
                url = OoklaProvider._download_url()

                # Check if the URL contains "armhf" (our expected machine mapping)
                self.assertIn("armhf", url)

    @mock.patch("platform.system", return_value="UnsupportedOS")
    @mock.patch("platform.machine", return_value="UnsupportedCPU")
    def test_unsupported_architecture(self, mock_machine, mock_system):
        """Test handling of unsupported OS/CPU combinations."""
        with self.assertRaises(PlatformNotSupported):
            _ = OoklaProvider(self.temp_dir)


class TestOoklaRealBinaries(unittest.TestCase):
    """Test actual Ookla binary operations across supported platforms."""

    def setUp(self):
        """Set up a clean test directory."""
        # Create a fresh temporary directory for each test
        self.temp_dir = tempfile.mkdtemp(prefix="ookla_test_")

    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.temp_dir)

    @pytest.mark.expensive
    def test_real_binary_download_all_platforms(self):
        """Test real non-simulated download and extraction of Ookla test binary for all supported platforms."""
        # Mock _parse_version to avoid executing binaries
        with mock.patch.object(OoklaProvider, "_parse_version", return_value=Version("1.0.0")):
            # Test results tracking
            results = []

            # Test each platform combination defined in OoklaProvider._DOWNLOAD_URLS
            for (sys_name, machine), _url in OoklaProvider._DOWNLOAD_URLS.items():
                # Create a dedicated directory for each platform
                platform_dir = os.path.join(self.temp_dir, f"{sys_name}-{machine}")
                os.makedirs(platform_dir, exist_ok=True)

                # Mock the platform detection to simulate this platform
                with (
                    mock.patch("platform.system", return_value=sys_name),
                    mock.patch("platform.machine", return_value=machine),
                ):
                    print(f"Testing: {sys_name} {machine}")

                    # Create a provider which will download the binary
                    provider = OoklaProvider(platform_dir)

                    # Check if binary exists
                    binary_exists = os.path.exists(provider.binary_path)

                    # Get file size if it exists
                    file_size = os.path.getsize(provider.binary_path) if binary_exists else 0

                    # Record result
                    results.append(
                        {
                            "system": sys_name,
                            "machine": machine,
                            "binary_path": provider.binary_path,
                            "exists": binary_exists,
                            "file_size": file_size,
                        }
                    )

                    # Verify binary was actually downloaded
                    self.assertTrue(
                        binary_exists, f"Binary not downloaded for {sys_name} {machine}"
                    )

                    # Verify binary has reasonable size
                    self.assertGreater(
                        file_size,
                        500000,
                        f"Binary file for {sys_name} {machine} is too small: {file_size} bytes",
                    )

                    # Verify the binary filename is correct
                    expected_filename = "speedtest.exe" if sys_name == "Windows" else "speedtest"
                    actual_filename = os.path.basename(provider.binary_path)
                    self.assertEqual(
                        actual_filename,
                        expected_filename,
                        f"Binary filename mismatch for {sys_name} {machine}",
                    )

            # Print test results summary
            print("\n=== Binary Download Test Results ===")
            for result in results:
                print(
                    f"{result['system']} {result['machine']}: "
                    f"{'✓' if result['exists'] else '✗'} "
                    f"({result['file_size']:,} bytes)"
                )

            # Success if we reach here
            self.assertEqual(
                len(results),
                len(OoklaProvider._DOWNLOAD_URLS),
                f"Tested {len(results)} of {len(OoklaProvider._DOWNLOAD_URLS)} platforms",
            )

    @pytest.mark.expensive
    def test_real_binary_download_and_version(self):
        """Test downloading the real binary for the current system and checking its version."""
        # Create a provider which will download the real binary for the current platform
        provider = OoklaProvider(self.temp_dir)

        # Verify binary was downloaded
        self.assertTrue(
            os.path.exists(provider.binary_path), f"Binary not downloaded at {provider.binary_path}"
        )

        # Verify binary has reasonable size
        file_size = os.path.getsize(provider.binary_path)
        self.assertGreater(file_size, 500000, f"Binary file is too small: {file_size} bytes")

        # Check that we got a real version (not 0)
        self.assertNotEqual(
            provider.version, Version("0"), "Failed to get a valid version from the binary"
        )

        print("\nSuccessfully downloaded and verified Ookla binary:")
        print(f"  Platform: {platform.system()} {platform.machine()}")
        print(f"  Binary path: {provider.binary_path}")
        print(f"  File size: {file_size:,} bytes")
        print(f"  Version: {provider.version}")


class TestNetworkHandling(unittest.TestCase):
    """Test handling of network errors."""

    def setUp(self):
        """Set up a clean test directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.temp_dir)

    @mock.patch("netvelocimeter.utils.binary_manager.urllib.request.urlopen")
    def test_network_errors(self, mock_urlopen):
        """Test handling of network errors."""
        mock_urlopen.side_effect = URLError("Network unreachable")

        with (
            self.assertRaises(URLError),
            mock.patch.object(OoklaProvider, "_parse_version", return_value=Version("1.0.0")),
        ):
            _ = OoklaProvider(self.temp_dir)


class TestOoklaRealMeasurement(unittest.TestCase):
    """Test real Ookla measurement."""

    def setUp(self):
        """Set up a clean test directory."""
        # Create a fresh temporary directory for each test
        self.temp_dir = tempfile.mkdtemp(prefix="ookla_test_")

    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.temp_dir)

    @pytest.mark.expensive
    def test_real_measurement(self):
        """Test real Ookla measurement."""
        # Create a provider which will download the real binary for the current platform
        provider = OoklaProvider(self.temp_dir)

        # Run a real speed test
        result = provider.measure()

        # Check if the result is valid
        self.assertIsNotNone(result)
        self.assertIsInstance(result.download_speed, (int, float))
        self.assertIsInstance(result.upload_speed, (int, float))
        self.assertIsInstance(result.ping_latency, timedelta)
        self.assertIsInstance(result.ping_jitter, timedelta)
        self.assertIsInstance(result.download_latency, timedelta)
        self.assertIsInstance(result.upload_latency, timedelta)
        self.assertIsInstance(result.packet_loss, (int, float))
        self.assertIsInstance(result.id, str)
        self.assertIsNotNone(result.server_info)
        self.assertIsNotNone(result.raw_result)
        self.assertGreater(result.download_speed, 0)
        self.assertGreater(result.upload_speed, 0)
        self.assertGreater(result.ping_latency.total_seconds(), 0)
        self.assertGreater(result.ping_jitter.total_seconds(), 0)
        self.assertGreater(result.download_latency.total_seconds(), 0)
        self.assertGreater(result.upload_latency.total_seconds(), 0)
        self.assertGreaterEqual(result.packet_loss, 0)

        print(result)
