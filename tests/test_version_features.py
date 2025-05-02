"""Unit tests for version-related features."""

import unittest
from unittest import mock

from packaging.version import Version

from netvelocimeter import NetVelocimeter


class TestVersionFeatures(unittest.TestCase):
    """Test version-related features."""

    @mock.patch("netvelocimeter.core.get_provider")
    def test_get_provider_version(self, mock_get_provider):
        """Test getting provider version."""
        # Create mock provider with version attribute (not method)
        mock_provider_instance = mock.MagicMock()
        # Set the version attribute to a Version object
        mock_provider_instance._version = Version("1.2.3.dev0")
        mock_provider_class = mock.MagicMock(return_value=mock_provider_instance)
        mock_get_provider.return_value = mock_provider_class

        nv = NetVelocimeter()
        version = nv.version

        # Compare with Version object, not string
        self.assertEqual(version, Version("1.2.3.dev0"))
