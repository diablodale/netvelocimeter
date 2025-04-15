"""
Tests for the Ookla provider.
"""

import json
import os
import tempfile
import unittest
from unittest import mock

from netvelocimeter.providers.ookla import OoklaProvider


class TestOoklaProvider(unittest.TestCase):
    """Tests for the Ookla provider."""

    @mock.patch('netvelocimeter.providers.ookla.OoklaProvider._ensure_binary')
    def setUp(self, mock_ensure_binary):
        """Set up the test."""
        mock_ensure_binary.return_value = "/fake/path"
        self.provider = OoklaProvider("/tmp")

    @mock.patch('subprocess.run')
    def test_measure(self, mock_run):
        """Test measuring network performance."""
        # Sample response data
        sample_data = {
            "download": {"bandwidth": 12500000},  # 100 Mbps
            "upload": {"bandwidth": 2500000},     # 20 Mbps
            "ping": {"latency": 15.5, "jitter": 2.1},
            "packetLoss": 0.1,
            "server": {
                "id": "12345",
                "name": "Test Server",
                "location": "Test Location",
                "host": "test.host.com"
            }
        }

        # Mock subprocess.run to return our sample data
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps(sample_data)
        mock_run.return_value = mock_process

        # Test full measurement
        result = self.provider.measure()
        self.assertEqual(result.download_speed, 100.0)  # 12500000 * 8 / 1_000_000
        self.assertEqual(result.upload_speed, 20.0)     # 2500000 * 8 / 1_000_000
        self.assertEqual(result.latency, 15.5)
        self.assertEqual(result.jitter, 2.1)
        self.assertEqual(result.packet_loss, 0.1)
        self.assertEqual(result.server_info["id"], "12345")

    @mock.patch('subprocess.run')
    def test_measure_download(self, mock_run):
        """Test measuring download speed."""
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps({"download": {"bandwidth": 12500000}})
        mock_run.return_value = mock_process

        speed = self.provider.measure_download()
        self.assertEqual(speed, 100.0)

        # Verify --no-upload was passed
        args, _ = mock_run.call_args
        self.assertIn("--no-upload", args[0])

    @mock.patch('subprocess.run')
    def test_measure_upload(self, mock_run):
        """Test measuring upload speed."""
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps({"upload": {"bandwidth": 2500000}})
        mock_run.return_value = mock_process

        speed = self.provider.measure_upload()
        self.assertEqual(speed, 20.0)

        # Verify --no-download was passed
        args, _ = mock_run.call_args
        self.assertIn("--no-download", args[0])

    @mock.patch('subprocess.run')
    def test_measure_latency(self, mock_run):
        """Test measuring latency."""
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps({"ping": {"latency": 15.5}})
        mock_run.return_value = mock_process

        latency = self.provider.measure_latency()
        self.assertEqual(latency, 15.5)

        # Verify both --no-download and --no-upload were passed
        args, _ = mock_run.call_args
        self.assertIn("--no-download", args[0])
        self.assertIn("--no-upload", args[0])

    @mock.patch('subprocess.run')
    def test_error_handling(self, mock_run):
        """Test error handling."""
        mock_process = mock.Mock()
        mock_process.returncode = 1
        mock_process.stderr = "Error message"
        mock_run.return_value = mock_process

        with self.assertRaises(RuntimeError):
            self.provider.measure()
