"""Ookla Speedtest.net provider implementation."""

from datetime import timedelta
import json
import platform
import re
import subprocess
from typing import Any

from packaging.version import InvalidVersion, Version

from ..core import register_provider
from ..exceptions import PlatformNotSupported
from ..terms import LegalTerms, LegalTermsCategory, LegalTermsCollection
from ..utils.binary_manager import BinaryManager
from .base import BaseProvider, MeasurementResult, ServerIDType, ServerInfo


class OoklaProvider(BaseProvider):
    """Provider for Ookla Speedtest.net."""

    # Class variables shared by all instances
    _DOWNLOAD_VERSION = "1.2.0"
    _DOWNLOAD_URLS = {
        (
            "windows",
            "amd64",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-win64.zip",
        (
            "linux",
            "x86_64",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-linux-x86_64.tgz",
        (
            "linux",
            "i386",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-linux-i386.tgz",
        (
            "linux",
            "aarch64",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-linux-aarch64.tgz",
        (
            "linux",
            "armel",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-linux-armel.tgz",
        (
            "linux",
            "armhf",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-linux-armhf.tgz",
        # (
        #    "darwin",
        #    "x86_64",
        # ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-macosx-universal.tgz",
        # (
        #    "darwin",
        #    "arm64",
        # ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-macosx-universal.tgz",
        # (
        #    "freebsd12",
        #    "x86_64",
        # ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-freebsd12-x86_64.pkg",
        # (
        #    "freebsd13",
        #    "x86_64",
        # ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-freebsd13-x86_64.pkg",
    }
    _TERMS_COLLECTION = [
        LegalTerms(
            text="You may only use this Speedtest software and information generated "
            "from it for personal, non-commercial use, through a command line "
            "interface on a personal computer. Your use of this software is subject "
            "to the End User License Agreement, Terms of Use and Privacy Policy.",
            url="https://www.speedtest.net/about/eula",
            category=LegalTermsCategory.EULA,
        ),
        LegalTerms(
            text="By using this Speedtest software, you agree to be bound by Ookla's Terms of Use.",
            url="https://www.speedtest.net/about/terms",
            category=LegalTermsCategory.SERVICE,
        ),
        LegalTerms(
            text="Ookla collects certain data through Speedtest that may be considered "
            "personally identifiable, such as your IP address, unique device "
            "identifiers or location. Ookla believes it has a legitimate interest "
            "to share this data with internet providers, hardware manufacturers and "
            "industry regulators to help them understand and create a better and "
            "faster internet. For further information including how the data may be "
            "shared, where the data may be transferred and Ookla's contact details, "
            "please see our Privacy Policy.",
            url="https://www.speedtest.net/about/privacy",
            category=LegalTermsCategory.PRIVACY,
        ),
    ]

    def __init__(
        self,
        custom_root: str | None = None,
    ):
        r"""Initialize the Ookla provider.

        Args:
            custom_root: Custom binary cache root directory for provider binaries
              - None (default) = platform-specific directory of
                posix `~/.local/bin/netvelocimeter`,
                windows `%%LOCALAPPDATA%%\netvelocimeter`
              - str = directory path for binary cache
        """
        # Call the base provider constructor
        super().__init__()

        # first create binary manager
        self._BINARY_MANAGER = BinaryManager(OoklaProvider, custom_root=custom_root)

        # then get binary path
        binary_filename = "speedtest.exe" if platform.system().lower() == "windows" else "speedtest"
        self._BINARY_PATH = self._BINARY_MANAGER.download_extract(
            url=OoklaProvider._download_url(), internal_filepath=binary_filename
        )

        # then set version derived from the binary
        self._VERSION = self._parse_version()

    @property
    def _version(self) -> Version:
        """Get the provider version.

        Returns:
            Version for this provider
        """
        return self._VERSION

    @classmethod
    def _legal_terms(
        cls, category: LegalTermsCategory = LegalTermsCategory.ALL
    ) -> LegalTermsCollection:
        """Get legal terms for Ookla Speedtest."""
        # Return the terms collection filtered by the requested category
        if category == LegalTermsCategory.ALL:
            return cls._TERMS_COLLECTION
        return [term for term in cls._TERMS_COLLECTION if term.category == category]

    @classmethod
    def _download_url(cls) -> str:
        """Get download URL for the compatible speedtest binary.

        Returns:
            Download URL for the compatible speedtest binary.
        """
        # e.g., Windows, Linux, Darwin;
        # on iOS and Android returns the user-facing OS name (i.e, 'iOS, 'iPadOS' or 'Android')
        system = platform.system().lower()

        # e.g., x86_64, i686, arm64
        machine = platform.machine().lower()

        # Map machine types to what Ookla expects
        if system == "linux":
            # Map x86 architectures
            if machine in ("x86_64", "amd64"):
                machine = "x86_64"
            elif machine in ("i386", "i486", "i586", "i686", "x86"):
                machine = "i386"
            # Map ARM architectures
            elif machine in ("aarch64", "arm64"):
                machine = "aarch64"
            elif machine.startswith("armv7") or machine.startswith("armhf"):
                machine = "armhf"  # 32-bit ARM with hardware floating point
            elif machine.startswith("armv6") or machine.startswith("armel"):
                machine = "armel"  # 32-bit ARM with software floating point

        # return the download URL based on the system and machine
        try:
            # Check if the key exists in the dictionary
            return cls._DOWNLOAD_URLS[(system, machine)]
        except KeyError:
            raise PlatformNotSupported(
                f"{cls.__name__} does not support {system} {machine}"
            ) from None

    def _parse_version(self) -> Version:
        """Get the version of the speedtest CLI as a Version object."""
        try:
            result = self._run_speedtest(["--version"], parse_json=False).get("stdout", "")
        except RuntimeError as e:
            # If the command fails, we can't determine the version
            raise InvalidVersion(f"Unable to determine Ookla version. {e}") from e

        # Parse version from output, e.g.
        # Speedtest by Ookla 1.2.0.84 (ea6b6773cf) Linux/x86_64-linux-musl 5.15.167.4-microsoft-standard-WSL2 x86_64    # noqa: E501
        match = re.match(r"^\s*[^0-9]+ ([0-9.]+)[^\da-fA-F]+([\da-fA-F]+)", result)
        if match:
            return Version(f"{match.group(1)}+{match.group(2)}")
        raise InvalidVersion(f"Unrecognized speedtest cli output: {result}")

    def _run_speedtest(
        self, args: list[str] | None = None, parse_json: bool = True
    ) -> dict[str, Any]:
        """Run the speedtest binary with the given arguments.

        Args:
            args: Additional arguments for the speedtest binary.
            parse_json: If True, parse the output as JSON.

        Returns:
            Parsed JSON output as a dictionary or raw stdout/stderr within a dictionary.

        Raises:
            RuntimeError: If the speedtest fails
        """
        cmd = [
            self._BINARY_PATH,
            "--progress=no",
            "--accept-license",
            "--accept-gdpr",
        ]
        if parse_json:
            cmd.append("--format=json")
        if args:
            cmd.extend(args)

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Check for errors
        if result.returncode != 0:
            raise RuntimeError(f"Speedtest failed: {result.stderr}")

        # Use explicit type cast, as JSON requires string keys, and json.loads checks for this
        if parse_json:
            return dict[str, Any](json.loads(result.stdout))
        return {"stdout": result.stdout, "stderr": result.stderr}

    @property
    def _servers(self) -> list[ServerInfo]:
        """Get a list of available servers.

        Returns:
            List of server information objects.
        """
        result = self._run_speedtest(["--servers"])

        servers = []
        for server in result.get("servers", []):
            servers.append(
                ServerInfo(
                    name=server.get("name"),
                    id=server.get("id"),
                    location=server.get("location"),
                    country=server.get("country"),
                    host=server.get("host"),
                    raw_server=server,
                )
            )

        return servers

    def _measure(
        self, server_id: ServerIDType | None = None, server_host: str | None = None
    ) -> MeasurementResult:
        """Run a complete speedtest.

        Args:
            server_id: Specific server ID to use for the test (integer or string)
            server_host: Specific server hostname to use for the test

        Returns:
            MeasurementResult with the test results.
        """
        run_args: list[str] = []
        if server_id is not None:
            run_args.extend(["--server-id", str(server_id)])
        elif server_host is not None:
            run_args.extend(["--host", server_host])

        result = self._run_speedtest(run_args)

        # Extract server information - ensure it exists
        server_data = result.get("server", {})
        if not server_data:
            raise ValueError("No server information found in speedtest results")
        server_info = ServerInfo(
            name=server_data.get("name"),
            id=server_data.get("id"),
            location=server_data.get("location"),
            country=server_data.get("country"),
            host=server_data.get("host"),
            raw_server=server_data,
        )

        # Get download/upload data with null safety
        download_data = result.get("download", {})
        upload_data = result.get("upload", {})

        # Convert bytes/s to Mbps (megabits per second)
        download_mbps = download_data.get("bandwidth") * 8 / 1_000_000
        upload_mbps = upload_data.get("bandwidth") * 8 / 1_000_000

        # Extract download and upload latency
        download_latency_ms = download_data.get("latency", {}).get("iqm", None)
        upload_latency_ms = upload_data.get("latency", {}).get("iqm", None)

        # Extract ping metrics
        ping_latency_ms = result.get("ping", {}).get("latency", None)
        ping_jitter_ms = result.get("ping", {}).get("jitter", None)

        # Extract result ID and persist URL if available
        result_data = result.get("result", {})
        result_id = result_data.get("id", None)
        persist_url = result_data.get("url", None) if result_data.get("persisted", False) else None

        # Convert to timedeltas
        return MeasurementResult(
            download_speed=download_mbps,
            upload_speed=upload_mbps,
            download_latency=timedelta(milliseconds=download_latency_ms),
            upload_latency=timedelta(milliseconds=upload_latency_ms),
            ping_latency=timedelta(milliseconds=ping_latency_ms),
            ping_jitter=timedelta(milliseconds=ping_jitter_ms),
            packet_loss=result.get("packetLoss"),
            server_info=server_info,
            persist_url=persist_url,
            id=result_id,
            raw_result=result,
        )


# Register this provider
register_provider("ookla", OoklaProvider)
register_provider("speedtest", OoklaProvider)  # Alias
