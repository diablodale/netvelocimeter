"""
Tests for the core functionality.
"""

import os
import tempfile
import unittest
from unittest import mock
from datetime import timedelta
from packaging.version import Version

from netvelocimeter import NetVelocimeter, get_provider
from netvelocimeter.providers.base import MeasurementResult


class TestNetVelocimeter(unittest.TestCase):
    """Tests for NetVelocimeter class."""

    def test_get_provider(self):
        """Test getting a provider."""
        provider_class = get_provider("ookla")
        self.assertIsNotNone(provider_class)

        # Test alias
        provider_class_alias = get_provider("speedtest")
        self.assertEqual(provider_class, provider_class_alias)

        # Test case insensitivity
        provider_class_case = get_provider("OoKlA")
        self.assertEqual(provider_class, provider_class_case)

    def test_invalid_provider(self):
        """Test getting an invalid provider."""
        with self.assertRaises(ValueError):
            get_provider("nonexistent")

    def test_initialize_with_binary_dir(self):
        """Test initializing with a binary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch('netvelocimeter.providers.ookla.OoklaProvider._ensure_binary') as mock_ensure:
                with mock.patch('netvelocimeter.providers.ookla.OoklaProvider._get_version') as mock_get_version:
                    mock_ensure.return_value = "/fake/path"
                    mock_get_version.return_value = "1.0.0-test"

                    nv = NetVelocimeter(binary_dir=temp_dir)
                    self.assertEqual(nv.provider.binary_dir, temp_dir)

    def test_provider_version_access(self):
        """Test accessing provider version."""
        # Mock the get_provider function instead of the OoklaProvider directly
        with mock.patch('netvelocimeter.core.get_provider') as mock_get_provider:
            # Create a mock provider class and instance
            mock_instance = mock.MagicMock()
            mock_instance.version = Version("1.2.3")
            mock_provider_class = mock.MagicMock(return_value=mock_instance)

            # Set up get_provider to return our mock provider class
            mock_get_provider.return_value = mock_provider_class

            nv = NetVelocimeter()
            self.assertEqual(nv.get_provider_version(), Version("1.2.3"))


class TestMeasurementResult(unittest.TestCase):
    """Tests for MeasurementResult class."""

    def test_str_representation(self):
        """Test string representation of measurement results."""
        result = MeasurementResult(
            download_speed=100.5,
            upload_speed=20.25,
            latency=timedelta(milliseconds=15.75),
            jitter=timedelta(milliseconds=3.5),
            packet_loss=0.1
        )

        str_result = str(result)
        # Check that output contains expected values
        self.assertIn("Download: 100.50 Mbps", str_result)
        self.assertIn("Upload: 20.25 Mbps", str_result)
        self.assertIn("Latency: 15.75 ms", str_result)
        self.assertIn("Jitter: 3.50 ms", str_result)
        self.assertIn("Packet Loss: 0.10%", str_result)
