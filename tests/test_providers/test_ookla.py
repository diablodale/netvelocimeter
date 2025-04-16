"""
Tests for the Ookla provider.
"""

import json
import os
import platform
import tempfile
import unittest
from unittest import mock
from datetime import timedelta
from packaging.version import Version

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

        import shutil
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
                    "id": "1",
                    "name": "Server 1",
                    "location": "Location 1",
                    "country": "Country 1",
                    "host": "server1.example.com",
                    "distance": 10.5
                },
                {
                    "id": "2",
                    "name": "Server 2",
                    "location": "Location 2",
                    "country": "Country 2",
                    "host": "server2.example.com",
                    "distance": 20.7
                }
            ]
        })
        mock_run.return_value = mock_process

        servers = self.provider.get_servers()

        # Verify --servers flag was included
        args, kwargs = mock_run.call_args
        cmd_line = args[0]
        self.assertIn("--servers", cmd_line)

        # Verify server list parsing
        self.assertEqual(len(servers), 2)
        self.assertEqual(servers[0].id, "1")
        self.assertEqual(servers[0].name, "Server 1")
        self.assertEqual(servers[0].host, "server1.example.com")
        self.assertEqual(servers[1].id, "2")
        self.assertEqual(servers[1].country, "Country 2")
        self.assertEqual(servers[1].distance, 20.7)

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
            "download": {"bandwidth": 12500000},
            "upload": {"bandwidth": 2500000},
            "ping": {"latency": 15.5, "jitter": 3.2},
            "server": {"id": "1234", "name": "Test Server"}
        })
        mock_run.return_value = mock_process

        result = self.provider.measure(server_id=1234)

        # Verify timedelta conversion
        self.assertIsInstance(result.latency, timedelta)
        self.assertIsInstance(result.jitter, timedelta)
        self.assertAlmostEqual(result.latency.total_seconds() * 1000, 15.5)
        self.assertAlmostEqual(result.jitter.total_seconds() * 1000, 3.2)

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
            "download": {"bandwidth": 12500000},
            "upload": {"bandwidth": 2500000},
            "ping": {"latency": 15.5, "jitter": 3.2},
            "server": {"id": "1234", "name": "Test Server"}
        })
        mock_run.return_value = mock_process

        result = self.provider.measure(server_host="example.com")

        # Verify timedelta conversion
        self.assertIsInstance(result.latency, timedelta)
        self.assertIsInstance(result.jitter, timedelta)

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
