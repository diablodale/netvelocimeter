"""Ookla Speedtest.net provider implementation."""

from datetime import timedelta
import json
import os
import platform
import re
import subprocess
from typing import Any

from packaging.version import InvalidVersion, Version

from ..core import register_provider
from ..exceptions import LegalAcceptanceError
from ..utils.binary_manager import download_file, ensure_executable, extract_file
from .base import (
    BaseProvider,
    MeasurementResult,
    ProviderLegalRequirements,
    ServerIDType,
    ServerInfo,
)


class OoklaProvider(BaseProvider):
    """Provider for Ookla Speedtest.net."""

    _BINARY_NAME = "speedtest"
    _DOWNLOAD_VERSION = "1.2.0"
    _DOWNLOAD_URLS = {
        (
            "Windows",
            "AMD64",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-win64.zip",
        (
            "Linux",
            "x86_64",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-linux-x86_64.tgz",
        (
            "Linux",
            "i386",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-linux-i386.tgz",
        (
            "Linux",
            "aarch64",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-linux-aarch64.tgz",
        (
            "Linux",
            "armel",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-linux-armel.tgz",
        (
            "Linux",
            "armhf",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-linux-armhf.tgz",
        (
            "Darwin",
            "x86_64",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-macosx-universal.tgz",
        (
            "Darwin",
            "arm64",
        ): f"https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-macosx-universal.tgz",
        # https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-freebsd12-x86_64.pkg
        # https://install.speedtest.net/app/cli/ookla-speedtest-{_DOWNLOAD_VERSION}-freebsd13-x86_64.pkg
    }

    def __init__(self, binary_dir: str):
        """Initialize the Ookla provider.

        Args:
            binary_dir: Directory to store the Ookla speedtest binary.
        """
        super().__init__(binary_dir)
        self.binary_path = self._ensure_binary()
        self.version = self._get_version()
        self._accepted_eula = False
        self._accepted_terms = False
        self._accepted_privacy = False

    @property
    def legal_requirements(self) -> ProviderLegalRequirements:
        """Get Ookla's legal requirements."""
        return ProviderLegalRequirements(
            eula_text="You may only use this Speedtest software and information generated "
            "from it for personal, non-commercial use, through a command line "
            "interface on a personal computer. Your use of this software is subject "
            "to the End User License Agreement, Terms of Use and Privacy Policy.",
            eula_url="https://www.speedtest.net/about/eula",
            # terms_text="By using this Speedtest software, you agree to be bound by Ookla's Terms of Use.",
            # terms_url="https://www.speedtest.net/about/terms",
            privacy_text="Ookla collects certain data through Speedtest that may be considered "
            "personally identifiable, such as your IP address, unique device "
            "identifiers or location. Ookla believes it has a legitimate interest "
            "to share this data with internet providers, hardware manufacturers and "
            "industry regulators to help them understand and create a better and "
            "faster internet. For further information including how the data may be "
            "shared, where the data may be transferred and Ookla's contact details, "
            "please see our Privacy Policy.",
            privacy_url="https://www.speedtest.net/about/privacy",
        )

    def _ensure_binary(self) -> str:
        """Ensure the Ookla speedtest binary is available.

        Returns:
            Path to the binary.
        """
        # e.g., Windows, Linux, Darwin;
        # on iOS and Android returns the user-facing OS name (i.e, 'iOS, 'iPadOS' or 'Android')
        system = platform.system()

        # e.g., x86_64, i686, arm64
        machine = platform.machine()

        # Map machine types to what Ookla expects
        if system == "Linux":
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

        key = (system, machine)
        if key not in self._DOWNLOAD_URLS:
            raise RuntimeError(f"No Ookla speedtest binary available for {system} {machine}")

        # Check if binary already exists
        binary_filename = "speedtest.exe" if system == "Windows" else "speedtest"
        binary_path = os.path.join(self.binary_dir, binary_filename)
        if os.path.exists(binary_path):
            return binary_path

        # Download and extract
        download_url = self._DOWNLOAD_URLS[key]
        temp_file = os.path.join(self.binary_dir, os.path.basename(download_url))

        try:
            # Download the file
            download_file(download_url, temp_file)

            # Extract the binary
            binary_path = extract_file(temp_file, binary_filename, self.binary_dir)

            # Make binary executable
            ensure_executable(binary_path)

            return binary_path
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def _get_version(self) -> Version:
        """Get the version of the speedtest CLI as a Version object."""
        result = subprocess.run([self.binary_path, "--version"], capture_output=True, text=True)

        if result.returncode != 0:
            # Return a zero version or None when we can't determine the version
            return Version("0")

        # Parse version from output, e.g.
        # Speedtest by Ookla 1.2.0.84 (ea6b6773cf) Linux/x86_64-linux-musl 5.15.167.4-microsoft-standard-WSL2 x86_64    # noqa: E501
        match = re.match(r"^\s*[^0-9]+ ([0-9.]+)[^\da-fA-F]+([\da-fA-F]+)", result.stdout)
        if match:
            try:
                return Version(f"{match.group(1)}+{match.group(2)}")
            except InvalidVersion:
                # If we can't parse the version, return a zero version
                pass
        return Version("0")

    def _run_speedtest(self, args: list[str] | None = None) -> dict[str, Any]:
        """Run the speedtest binary with the given arguments.

        Args:
            args: Additional arguments for the speedtest binary.

        Returns:
            Parsed JSON output from speedtest.
        """
        # Only add these flags if user has accepted the terms
        cmd = [self.binary_path, "--format=json", "--progress=no"]

        # These flags won't work unless user has explicitly accepted
        if self._accepted_eula and self._accepted_terms and self._accepted_privacy:
            cmd.extend(["--accept-license", "--accept-gdpr"])

        if args:
            cmd.extend(args)

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Special handling for acceptance errors
        if result.returncode != 0:
            stderr = result.stderr.lower()
            if "license" in stderr or "gdpr" in stderr or "accept" in stderr or "terms" in stderr:
                raise LegalAcceptanceError(
                    "You must accept the Ookla EULA, Terms of Service, and Privacy Policy before running tests."
                )
            raise RuntimeError(f"Speedtest failed: {result.stderr}")

        # Use explicit type cast, as JSON requires string keys, and json.loads checks for this
        return dict[str, Any](json.loads(result.stdout))

    def get_servers(self) -> list[ServerInfo]:
        """Get a list of available servers.

        Returns:
            List of server information objects.
        """
        result = self._run_speedtest(["--servers"])

        servers = []
        for server in result.get("servers", []):
            servers.append(
                ServerInfo(
                    name=server.get("name"),  # BUGBUG do not allow unknown names
                    id=server.get("id"),
                    location=server.get("location"),
                    country=server.get("country"),
                    host=server.get("host"),
                    raw_server=server,
                )
            )

        return servers

    def measure(
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
            name=server_data.get("name"),  # BUGBUG do not allow unknown names
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
