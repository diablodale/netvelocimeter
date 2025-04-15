"""
Tests for the core functionality.
"""

import os
import tempfile
import unittest
from unittest import mock

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
            # Mock _ensure_binary to avoid actual downloads
            with mock.patch('netvelocimeter.providers.ookla.OoklaProvider._ensure_binary') as mock_ensure:
                mock_ensure.return_value = "/fake/path"
                nv = NetVelocimeter(binary_dir=temp_dir)
                self.assertEqual(nv.provider.binary_dir, temp_dir)


class TestMeasurementResult(unittest.TestCase):
    """Tests for MeasurementResult class."""

    def test_str_representation(self):
        """Test string representation of measurement results."""
        result = MeasurementResult(
            download_speed=100.5,
            upload_speed=20.25,
            latency=15.75,
            jitter=3.5,
            packet_loss=0.1
        )

        str_result = str(result)
        self.assertIn("Download: 100.50 Mbps", str_result)
        self.assertIn("Upload: 20.25 Mbps", str_result)
        self.assertIn("Latency: 15.75 ms", str_result)
        self.assertIn("Jitter: 3.50 ms", str_result)
        self.assertIn("Packet Loss: 0.10%", str_result)
