"""Test server list and server selection features."""

from datetime import timedelta
import unittest
from unittest import mock

from netvelocimeter import NetVelocimeter
from netvelocimeter.providers.base import MeasurementResult, ServerInfo


class TestServerFeatures(unittest.TestCase):
    """Test server list and server selection features."""

    def setUp(self):
        """Set up test environment."""
        self.mock_provider = mock.MagicMock()

        # Configure mock provider
        self.mock_provider.measure.return_value = MeasurementResult(
            download_speed=100.0,
            upload_speed=50.0,
            ping_latency=timedelta(milliseconds=10.0),
            ping_jitter=timedelta(milliseconds=2.0),
        )

        # Create server list
        server1 = ServerInfo(
            id="1",
            name="Server 1",
            location="Location 1",
            country="Country 1",
            host="host1.example.com",
        )
        server2 = ServerInfo(
            id="2",
            name="Server 2",
            location="Location 2",
            country="Country 2",
            host="host2.example.com",
        )
        self.mock_provider.get_servers.return_value = [server1, server2]

    @mock.patch("netvelocimeter.core.get_provider")
    def test_get_servers(self, mock_get_provider):
        """Test getting server list."""
        mock_get_provider.return_value = lambda x: self.mock_provider

        nv = NetVelocimeter()
        servers = nv.get_servers()

        self.assertEqual(len(servers), 2)
        self.assertEqual(servers[0].id, "1")
        self.assertEqual(servers[0].name, "Server 1")
        self.assertEqual(servers[0].host, "host1.example.com")
        self.assertEqual(servers[1].id, "2")
        self.assertEqual(servers[1].location, "Location 2")
        self.assertEqual(servers[1].country, "Country 2")

    @mock.patch("netvelocimeter.core.get_provider")
    def test_measurement_with_server_id(self, mock_get_provider):
        """Test measuring with specific server ID."""
        mock_get_provider.return_value = lambda x: self.mock_provider

        nv = NetVelocimeter()

        # Test with int ID
        _ = nv.measure(server_id=1)  # Integer

        _args, kwargs = self.mock_provider.measure.call_args
        self.assertEqual(kwargs["server_id"], 1)

        # Test with string ID
        _ = nv.measure(server_id="abc123")  # String

        _args, kwargs = self.mock_provider.measure.call_args
        self.assertEqual(kwargs["server_id"], "abc123")

    @mock.patch("netvelocimeter.core.get_provider")
    def test_measurement_with_server_host(self, mock_get_provider):
        """Test measuring with specific server host."""
        mock_get_provider.return_value = lambda x: self.mock_provider

        nv = NetVelocimeter()
        nv.measure(server_host="example.com")

        # Verify server_host was passed to provider's measure method
        _args, kwargs = self.mock_provider.measure.call_args
        self.assertEqual(kwargs["server_host"], "example.com")
