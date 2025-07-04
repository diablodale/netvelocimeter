"""Test server list and server selection features."""

from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from packaging.version import Version

from netvelocimeter import NetVelocimeter
from netvelocimeter.legal import LegalTermsCategory
from netvelocimeter.providers.base import BaseProvider, MeasurementResult, ServerInfo
from netvelocimeter.utils.rates import DataRateMbps, TimeDuration


class ServerFeaturesMockProvider(BaseProvider):
    """Mock provider for testing server features."""

    @property
    def _version(self) -> Version:
        """Return a mock version."""
        return Version("1.0.0")

    def _legal_terms(self, categories=LegalTermsCategory.ALL):
        """Return mock legal terms."""
        return []

    @property
    def _servers(self) -> list[ServerInfo]:
        """Return a list of mock servers."""
        return [
            ServerInfo(
                id="1",
                name="Server 1",
                location="Location 1",
                country="Country 1",
                host="host1.example.com",
            ),
            ServerInfo(
                id="2",
                name="Server 2",
                location="Location 2",
                country="Country 2",
                host="host2.example.com",
            ),
        ]

    def _measure(self, server_id=None, server_host=None):
        """Return mock measurement results."""
        return MeasurementResult(
            download_speed=DataRateMbps(100.0),
            upload_speed=DataRateMbps(50.0),
            ping_latency=TimeDuration(milliseconds=10.0),
            ping_jitter=TimeDuration(milliseconds=2.0),
            server_info=ServerInfo(
                id=server_id if server_id else 832476,
                name=f"Server {server_host}{server_id}",
                location="Location x",
                country="Country x",
                host=f"{server_host or server_id}.example.com",
            ),
        )


class TestServerFeatures(unittest.TestCase):
    """Test server list and server selection features."""

    @mock.patch("netvelocimeter.core.get_provider")
    def test_get_servers(self, mock_get_provider):
        """Test getting server list."""
        mock_get_provider.return_value = ServerFeaturesMockProvider

        nv = NetVelocimeter()
        servers = nv.servers

        self.assertEqual(len(servers), 2)
        self.assertEqual(servers[0].id, "1")
        self.assertEqual(servers[0].name, "Server 1")
        self.assertEqual(servers[0].host, "host1.example.com")
        self.assertEqual(servers[1].id, "2")
        self.assertEqual(servers[1].location, "Location 2")
        self.assertEqual(servers[1].country, "Country 2")

    def test_get_servers_static(self):
        """Test getting static server list."""
        with TemporaryDirectory() as temp_dir:
            # create nv with static provider
            nv = NetVelocimeter(provider="static", config_root=temp_dir)

            # accept all terms
            nv.accept_terms(nv.legal_terms())

            # get servers
            servers = nv.servers

            self.assertEqual(len(servers), 5)
            for i in range(1, 6):
                self.assertEqual(servers[i - 1].id, i)
                self.assertEqual(servers[i - 1].name, f"Test Server {i}")
                self.assertEqual(servers[i - 1].host, f"test{i}.example.com")
                self.assertEqual(servers[i - 1].location, f"Test Location {i}")
                self.assertEqual(servers[i - 1].country, "Test Country")

    @mock.patch("netvelocimeter.core.get_provider")
    def test_measurement_with_server_id(self, mock_get_provider):
        """Test measuring with specific server ID."""
        mock_get_provider.return_value = ServerFeaturesMockProvider
        nv = NetVelocimeter()

        # Test with int ID
        result = nv.measure(server_id=1999)
        self.assertTrue(result.server_info.name)
        self.assertEqual(result.server_info.id, 1999)
        self.assertEqual(result.server_info.host, "1999.example.com")

        # Test with string ID
        result = nv.measure(server_id="abc123")
        self.assertTrue(result.server_info.name)
        self.assertEqual(result.server_info.id, "abc123")
        self.assertEqual(result.server_info.host, "abc123.example.com")

    @mock.patch("netvelocimeter.core.get_provider")
    def test_measurement_with_server_host(self, mock_get_provider):
        """Test measuring with specific server host."""
        mock_get_provider.return_value = ServerFeaturesMockProvider
        nv = NetVelocimeter()

        # Test with server host
        result = nv.measure(server_host="myisphost")
        self.assertTrue(result.server_info.name)
        self.assertEqual(result.server_info.host, "myisphost.example.com")
        self.assertEqual(result.server_info.id, 832476)

    @mock.patch("netvelocimeter.core.get_provider")
    def test_format_representation(self, mock_get_provider):
        """Test format representation of server info."""
        mock_get_provider.return_value = ServerFeaturesMockProvider
        nv = NetVelocimeter()

        # Get the first server
        server = nv.servers[0]

        # Check format representation
        expected = (
            r"name:\s+Server 1\n"
            r"id:\s+1\n"
            r"host:\s+host1.example.com\n"
            r"location:\s+Location 1\n"
            r"country:\s+Country 1"
        )
        self.assertRegex(format(server), expected)
