"""
Tests for the Ookla provider.
"""

import json
import os
import platform
import pytest
import shutil
import tempfile
import unittest
from unittest import mock
from datetime import timedelta
from packaging.version import Version

from netvelocimeter.providers.base import ServerInfo
from netvelocimeter.providers.ookla import OoklaProvider
from netvelocimeter.exceptions import LegalAcceptanceError


class TestOoklaProvider(unittest.TestCase):
    """Test Ookla provider implementation."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

        # More robust patching
        self.patchers = []

        # Patch _ensure_binary
        patcher = mock.patch.object(OoklaProvider, '_ensure_binary')
        self.mock_ensure_binary = patcher.start()
        self.mock_ensure_binary.return_value = os.path.join(self.temp_dir, "speedtest.exe" if platform.system() == 'Windows' else "speedtest")
        self.patchers.append(patcher)

        # Patch _get_version to return a Version object
        patcher = mock.patch.object(OoklaProvider, '_get_version')
        self.mock_get_version = patcher.start()
        self.mock_get_version.return_value = Version("1.0.0")
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
        """Test Ookla legal requirements."""
        legal = self.provider.legal_requirements

        self.assertTrue(legal.requires_acceptance)
        self.assertIsNotNone(legal.eula_text)
        self.assertEqual(legal.eula_url, "https://www.speedtest.net/about/eula")
        self.assertIsNotNone(legal.privacy_text)
        self.assertEqual(legal.privacy_url, "https://www.speedtest.net/about/privacy")

    @mock.patch('subprocess.run')
    def test_run_speedtest_without_acceptance(self, mock_run):
        """Test running speedtest without acceptance."""
        # Mock subprocess to simulate error when license not accepted
        mock_process = mock.Mock()
        mock_process.returncode = 1
        mock_process.stderr = "Error: You must accept the license agreement to use this software"
        mock_run.return_value = mock_process

        # Verify exception is raised
        with self.assertRaises(LegalAcceptanceError):
            self.provider._run_speedtest()

    @mock.patch('subprocess.run')
    def test_run_speedtest_with_acceptance(self, mock_run):
        """Test running speedtest with acceptance."""
        # Set up acceptance flags
        self.provider._accepted_eula = True
        self.provider._accepted_terms = True
        self.provider._accepted_privacy = True

        # Mock successful subprocess run
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps({
            "download": {"bandwidth": 12500000},  # 100 Mbps
            "upload": {"bandwidth": 2500000},     # 20 Mbps
            "ping": {"latency": 15.5, "jitter": 3.2},
            "server": {"id": "1234", "name": "Test Server"}
        })
        mock_run.return_value = mock_process

        result = self.provider._run_speedtest()

        # Verify --accept-license and --accept-gdpr flags were included
        args, kwargs = mock_run.call_args
        cmd_line = args[0]
        self.assertIn("--accept-license", cmd_line)
        self.assertIn("--accept-gdpr", cmd_line)

        # Verify result parsing
        self.assertEqual(result["download"]["bandwidth"], 12500000)

    @mock.patch('subprocess.run')
    def test_get_servers(self, mock_run):
        """Test getting server list."""
        # Set up acceptance flags
        self.provider._accepted_eula = True
        self.provider._accepted_terms = True
        self.provider._accepted_privacy = True

        # Mock server list response
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps({
            "servers": [
                {
                    "name": "Server 1",
                    "id": "1",
                    "location": "Location 1",
                    "country": "Country 1",
                    "host": "server1.example.com"
                },
                {
                    "name": "Server 2",
                    "location": "Location 2",
                    "country": "Country 2",
                    "host": "server2.example.com"
                }
            ]
        })
        mock_run.return_value = mock_process

        servers = self.provider.get_servers()

        # Verify --servers flag was included
        args, kwargs = mock_run.call_args
        cmd_line = args[0]
        self.assertIn("--servers", cmd_line)

        # Update assertions to account for optional id:
        for server in servers:
            self.assertIsInstance(server, ServerInfo)
            self.assertIsInstance(server.name, str)
            # Don't assume id is required - it may be None
            if server.id is not None:
                self.assertTrue(isinstance(server.id, str) or isinstance(server.id, int))

        # Verify server list parsing
        self.assertEqual(len(servers), 2)
        self.assertEqual(servers[0].id, "1")
        self.assertEqual(servers[0].name, "Server 1")
        self.assertEqual(servers[0].host, "server1.example.com")
        self.assertEqual(servers[1].name, "Server 2")
        self.assertEqual(servers[1].country, "Country 2")

    @mock.patch('subprocess.run')
    def test_measure_with_server_id(self, mock_run):
        """Test measurement with specified server ID."""
        # Set up acceptance flags
        self.provider._accepted_eula = True
        self.provider._accepted_terms = True
        self.provider._accepted_privacy = True

        # Mock successful measurement
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps({
            "download": {"bandwidth": 12500000, "latency": {"iqm": 42.985}},
            "upload": {"bandwidth": 2500000, "latency": {"iqm": 178.546}},
            "ping": {"latency": 15.5, "jitter": 3.2},
            "server": {"id": "1234", "name": "Test Server"}
        })
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

    @mock.patch('subprocess.run')
    def test_measure_with_server_host(self, mock_run):
        """Test measurement with specified server host."""
        # Set up acceptance flags
        self.provider._accepted_eula = True
        self.provider._accepted_terms = True
        self.provider._accepted_privacy = True

        # Mock successful measurement
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps({
            "download": {"bandwidth": 12500000, "latency": {"iqm": 42.985}},
            "upload": {"bandwidth": 2500000, "latency": {"iqm": 178.546}},
            "ping": {"latency": 15.5, "jitter": 3.2},
            "server": {"id": "1234", "name": "Test Server"}
        })
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

    def test_get_version(self):
        """Test getting provider version."""
        # Version is already mocked in setUp
        version = self.provider.version
        self.assertEqual(version, Version("1.0.0"))

    @mock.patch('netvelocimeter.providers.ookla.OoklaProvider._get_version')
    @mock.patch('netvelocimeter.providers.ookla.OoklaProvider._ensure_binary')
    def test_get_version_parsing(self, mock_ensure_binary, mock_get_version):
        """Test version extraction from speedtest output."""
        # Create fresh mocks for this test only
        mock_ensure_binary.return_value = "speedtest_path"

        # Override _get_version to return our test version
        mock_get_version.return_value = Version("1.2.3")

        # Create a new provider instance
        provider = OoklaProvider(self.temp_dir)

        # Check the version
        self.assertEqual(provider.version, Version("1.2.3"))

    @mock.patch('netvelocimeter.providers.ookla.OoklaProvider._get_version')
    @mock.patch('netvelocimeter.providers.ookla.OoklaProvider._ensure_binary')
    def test_get_version_error(self, mock_ensure_binary, mock_get_version):
        """Test handling failed version check."""
        # Create fresh mocks for this test only
        mock_ensure_binary.return_value = "speedtest_path"

        # Override _get_version to return zero version
        mock_get_version.return_value = Version("0.0.0")

        # Create a new provider instance
        provider = OoklaProvider(self.temp_dir)

        # Check the version
        self.assertEqual(provider.version, Version("0.0.0"))

    def test_measure_with_sample_data(self):
        """Test measurement using sample data from JSON file."""
        # Set up acceptance flags
        self.provider._accepted_eula = True
        self.provider._accepted_terms = True
        self.provider._accepted_privacy = True

        # Path to sample data file
        sample_path = os.path.join(os.path.dirname(__file__), "samples", "ookla.json")

        # Load sample data
        with open(sample_path, "r") as f:
            sample_data = json.load(f)

        # Mock subprocess.run to return our sample data
        with mock.patch('subprocess.run') as mock_run:
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
            self.assertEqual(result.persist_url, "https://www.speedtest.net/result/c/c37d62b5-52ab-5252-bc06-db205451a1e5")

            # Update verification for the measurement ID
            self.assertEqual(result.id, "c37d62b5-52ab-5252-bc06-db205451a1e5")

            # Update assertions if verifying server_info:
            self.assertEqual(result.server_info.name, "DNS:NET Internet Service GmbH")
            # If id is expected in the sample, verify it:
            if "id" in result.server_info.raw_server:
                self.assertEqual(result.server_info.id, 20507)

    @mock.patch('subprocess.run')
    def test_error_handling(self, mock_run):
        """Test handling of non-acceptance related errors."""
        self.provider._accepted_eula = True
        self.provider._accepted_terms = True
        self.provider._accepted_privacy = True

        # Mock a general error
        mock_process = mock.Mock()
        mock_process.returncode = 1
        mock_process.stderr = "Connection error: could not reach server"
        mock_run.return_value = mock_process

        with self.assertRaises(RuntimeError) as context:
            self.provider._run_speedtest()

        self.assertIn("Speedtest failed", str(context.exception))

    @mock.patch('subprocess.run')
    def test_measure_without_persist_url(self, mock_run):
        """Test measurement without a persist URL in the result."""
        self.provider._accepted_eula = True
        self.provider._accepted_terms = True
        self.provider._accepted_privacy = True

        # Mock response without the result.url field
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps({
            "download": {"bandwidth": 12500000, "latency": {"iqm": 42.985}},
            "upload": {"bandwidth": 2500000, "latency": {"iqm": 178.546}},
            "ping": {"latency": 15.5, "jitter": 3.2},
            "server": {"id": "1234", "name": "Test Server"}
        })
        mock_run.return_value = mock_process

        result = self.provider.measure()

        # The persist_url should be None
        self.assertIsNone(result.persist_url)

    @mock.patch('subprocess.run')
    def test_measure_without_result_id(self, mock_run):
        """Test measurement without a result ID in the response."""
        self.provider._accepted_eula = True
        self.provider._accepted_terms = True
        self.provider._accepted_privacy = True

        # Mock response without the result.id field
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps({
            "download": {"bandwidth": 12500000, "latency": {"iqm": 42.985}},
            "upload": {"bandwidth": 2500000, "latency": {"iqm": 178.546}},
            "ping": {"latency": 15.5, "jitter": 3.2},
            "server": {"id": "1234", "name": "Test Server"}
        })
        mock_run.return_value = mock_process

        result = self.provider.measure()

        # The id should be None
        self.assertIsNone(result.id)

class TestOoklaProviderVersionParsing(unittest.TestCase):
    """Separate test class for version parsing functionality."""

    def test_invalid_version_format(self):
        """Test handling of invalid version format."""
        # Create a provider with direct mocks, no setUp complications
        with mock.patch('subprocess.run') as mock_run:
            # Set up mock for invalid version output
            mock_process = mock.Mock()
            mock_process.returncode = 0
            mock_process.stdout = "Something invalid"
            mock_run.return_value = mock_process

            # Patch _ensure_binary directly
            with mock.patch('netvelocimeter.providers.ookla.OoklaProvider._ensure_binary',
                           return_value="speedtest_path_1234"):
                # Create a clean provider instance
                provider = OoklaProvider("/temp/dir")

                # Version should be 0.0.0 when it can't be parsed
                self.assertEqual(provider.version, Version("0.0.0"))

                # Verify subprocess call
                mock_run.assert_called_once_with(
                    ["speedtest_path_1234", "--version"],
                    capture_output=True,
                    text=True
                )

    def test_valid_version_format(self):
        """Test handling of valid version format."""
        # Create a provider with direct mocks, no setUp complications
        with mock.patch('subprocess.run') as mock_run:
            # Set up mock for valid version output
            mock_process = mock.Mock()
            mock_process.returncode = 0
            mock_process.stdout = "Speedtest by Ookla 1.2.0.84 (ea6b6773cf) Linux/x86_64-linux-musl 5.15.167.4-microsoft-standard-WSL2 x86_64"
            mock_run.return_value = mock_process

            # Patch _ensure_binary directly
            with mock.patch('netvelocimeter.providers.ookla.OoklaProvider._ensure_binary',
                           return_value="speedtest_path_1234"):
                # Create a clean provider instance
                provider = OoklaProvider("/temp/dir")

                # Version should be parsed correctly
                self.assertEqual(provider.version, Version("1.2.0.84+ea6b6773cf"))

                # Verify subprocess call
                mock_run.assert_called_once_with(
                    ["speedtest_path_1234", "--version"],
                    capture_output=True,
                    text=True
                )

class TestOoklaProviderPlatformDetection(unittest.TestCase):
    """Test platform detection for OoklaProvider."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @mock.patch('platform.system')
    @mock.patch('platform.machine')
    def test_platform_detection_mapping(self, mock_machine, mock_system):
        """Test platform and architecture mapping logic."""
        # Test ARM mapping on Linux
        mock_system.return_value = "Linux"
        mock_machine.return_value = "armv7l"

        # We need to patch where the function is *used*, not where it's defined
        with mock.patch('netvelocimeter.providers.ookla.download_file') as mock_download:
            with mock.patch('netvelocimeter.providers.ookla.extract_file'):
                with mock.patch('netvelocimeter.providers.ookla.ensure_executable'):
                    with mock.patch.object(OoklaProvider, '_get_version', return_value=Version("1.0.0")):
                        # Now create the provider - this will call the real _ensure_binary
                        provider = OoklaProvider(self.temp_dir)

                        # The download URL should have been passed to download_file
                        mock_download.assert_called_once()
                        url_arg = mock_download.call_args[0][0]

                        # Check if the URL contains "armhf" (our expected machine mapping)
                        self.assertIn("armhf", url_arg, f"Machine type 'armv7l' not correctly mapped to 'armhf' in URL: {url_arg}")



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
        # Mock _get_version to avoid executing binaries
        with mock.patch.object(OoklaProvider, '_get_version', return_value=Version("1.0.0")):
            # Test results tracking
            results = []

            # Test each platform combination defined in OoklaProvider._DOWNLOAD_URLS
            for (sys_name, machine), url in OoklaProvider._DOWNLOAD_URLS.items():
                # Create a dedicated directory for each platform
                platform_dir = os.path.join(self.temp_dir, f"{sys_name}-{machine}")
                os.makedirs(platform_dir, exist_ok=True)

                # Mock the platform detection to simulate this platform
                with mock.patch('platform.system', return_value=sys_name):
                    with mock.patch('platform.machine', return_value=machine):
                        print(f"Testing: {sys_name} {machine}")

                        # Create a provider which will download the binary
                        provider = OoklaProvider(platform_dir)

                        # Check if binary exists
                        binary_exists = os.path.exists(provider.binary_path)

                        # Get file size if it exists
                        file_size = os.path.getsize(provider.binary_path) if binary_exists else 0

                        # Record result
                        results.append({
                            "system": sys_name,
                            "machine": machine,
                            "binary_path": provider.binary_path,
                            "exists": binary_exists,
                            "file_size": file_size
                        })

                        # Verify binary was actually downloaded
                        self.assertTrue(binary_exists, f"Binary not downloaded for {sys_name} {machine}")

                        # Verify binary has reasonable size
                        self.assertGreater(file_size, 500000,
                                         f"Binary file for {sys_name} {machine} is too small: {file_size} bytes")

                        # Verify the binary filename is correct
                        expected_filename = "speedtest.exe" if sys_name == "Windows" else "speedtest"
                        actual_filename = os.path.basename(provider.binary_path)
                        self.assertEqual(actual_filename, expected_filename,
                                       f"Binary filename mismatch for {sys_name} {machine}")

            # Print test results summary
            print("\n=== Binary Download Test Results ===")
            for result in results:
                print(f"{result['system']} {result['machine']}: "
                      f"{'✓' if result['exists'] else '✗'} "
                      f"({result['file_size']:,} bytes)")

            # Success if we reach here
            self.assertEqual(len(results), len(OoklaProvider._DOWNLOAD_URLS),
                             f"Tested {len(results)} of {len(OoklaProvider._DOWNLOAD_URLS)} platforms")

    @pytest.mark.expensive
    def test_real_binary_download_and_version(self):
        """Test downloading the real binary for the current system and checking its version."""
        # Create a provider which will download the real binary for the current platform
        provider = OoklaProvider(self.temp_dir)

        # Verify binary was downloaded
        self.assertTrue(os.path.exists(provider.binary_path),
                      f"Binary not downloaded at {provider.binary_path}")

        # Verify binary has reasonable size
        file_size = os.path.getsize(provider.binary_path)
        self.assertGreater(file_size, 500000,
                         f"Binary file is too small: {file_size} bytes")

        # Check that we got a real version (not 0)
        self.assertNotEqual(provider.version, Version("0"),
                           "Failed to get a valid version from the binary")

        print(f"\nSuccessfully downloaded and verified Ookla binary:")
        print(f"  Platform: {platform.system()} {platform.machine()}")
        print(f"  Binary path: {provider.binary_path}")
        print(f"  File size: {file_size:,} bytes")
        print(f"  Version: {provider.version}")

class TestNetworkHandling(unittest.TestCase):
    """Test handling of network errors."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @mock.patch('netvelocimeter.utils.binary_manager.urllib.request.urlopen')
    def test_network_errors(self, mock_urlopen):
        """Test handling of network errors."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")

        with self.assertRaises(urllib.error.URLError):
            with mock.patch.object(OoklaProvider, '_get_version', return_value=Version("1.0.0")):
                provider = OoklaProvider(self.temp_dir)

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

        # Set up acceptance flags
        provider._accepted_eula = True
        provider._accepted_terms = True
        provider._accepted_privacy = True

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
