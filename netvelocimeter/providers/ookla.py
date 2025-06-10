"""Ookla Speedtest.net provider implementation."""

import json
import re
import subprocess
from typing import Any

from packaging.version import InvalidVersion, Version

from ..core import register_provider
from ..legal import (
    LegalTerms,
    LegalTermsCategory,
    LegalTermsCategoryCollection,
    LegalTermsCollection,
)
from ..utils.binary_manager import BinaryManager, BinaryMeta, select_platform_binary
from ..utils.rates import DataRateMbps, Percentage, TimeDuration
from .base import BaseProvider, MeasurementResult, ServerIDType, ServerInfo


class OoklaProvider(BaseProvider):
    """Provider for Ookla Speedtest.net, uses the official Ookla Speedtest CLI tool."""

    # Class variables shared by all instances
    _PLATFORM_BINARIES = {
        (
            "windows",
            "x86_64",
        ): BinaryMeta(
            url="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-win64.zip",
            internal_filepath="speedtest.exe",
            hash_sha256="13e3d888b845d301a556419e31f14ab9bff57e3f06089ef2fd3bdc9ba6841efa",
        ),
        (
            "linux",
            "x86_64",
        ): BinaryMeta(
            url="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-x86_64.tgz",
            internal_filepath="speedtest",
            hash_sha256="5690596c54ff9bed63fa3732f818a05dbc2db19ad36ed68f21ca5f64d5cfeeb7",
        ),
        (
            "linux",
            "x86_32",
        ): BinaryMeta(
            url="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-i386.tgz",
            internal_filepath="speedtest",
            hash_sha256="9ff7e18dbae7ee0e03c66108445a2fb6ceea6c86f66482e1392f55881b772fe8",
        ),
        (
            "linux",
            "arm64",
        ): BinaryMeta(
            url="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-aarch64.tgz",
            internal_filepath="speedtest",
            hash_sha256="3953d231da3783e2bf8904b6dd72767c5c6e533e163d3742fd0437affa431bd3",
        ),
        (
            "linux",
            "armel",
        ): BinaryMeta(
            url="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-armel.tgz",
            internal_filepath="speedtest",
            hash_sha256="629a455a2879224bd0dbd4b36d8c721dda540717937e4660b4d2c966029466bf",
        ),
        (
            "linux",
            "armhf",
        ): BinaryMeta(
            url="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-armhf.tgz",
            internal_filepath="speedtest",
            hash_sha256="e45fcdebbd8a185553535533dd032d6b10bc8c64eee4139b1147b9c09835d08d",
        ),
        # (
        #     "darwin",
        #     "x86_64",
        # ): BinaryMeta(
        #     url="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-macosx-universal.tgz",
        #     internal_filepath="speedtest",
        #     hash_sha256="",
        # ),
        # (
        #     "darwin",
        #     "arm64",
        # ): BinaryMeta(
        #     url="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-macosx-universal.tgz",
        #     internal_filepath="speedtest",
        #     hash_sha256="",
        # ),
        # (
        #     "freebsd11",
        #     "x86_64",
        # ): BinaryMeta(
        #     url="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-freebsd11-x86_64.pkg",
        #     internal_filepath="speedtest",
        #     hash_sha256="",
        # ),
        # (
        #     "freebsd12",
        #     "x86_64",
        # ): BinaryMeta(
        #     url="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-freebsd12-x86_64.pkg",
        #     internal_filepath="speedtest",
        #     hash_sha256="",
        # ),
        # (
        #     "freebsd13",
        #     "x86_64",
        # ): BinaryMeta(
        #     url="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-freebsd13-x86_64.pkg",
        #     internal_filepath="speedtest",
        #     hash_sha256="",
        # ),
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
        *,
        config_root: str | None = None,
        bin_root: str | None = None,
    ):
        r"""Initialize the Ookla provider.

        Args:
            config_root: Directory to store configuration, e.g. legal acceptance
                - None: Use default location (%%APPDATA%%\netvelocimeter or ~/.config/netvelocimeter)
                - str: Custom directory path
            bin_root: Custom binary cache root directory for provider binaries
              - None (default) = platform-specific directory of
                posix `~/.local/bin/netvelocimeter`,
                windows `%%LOCALAPPDATA%%\netvelocimeter`
              - str = directory path for binary cache
        """
        # Call the base provider constructor
        super().__init__(config_root=config_root)

        # first create binary manager
        self._BINARY_MANAGER = BinaryManager(OoklaProvider, bin_root=bin_root)

        # get target binary
        binary_meta = select_platform_binary(self._PLATFORM_BINARIES)
        self._BINARY_PATH = self._BINARY_MANAGER.download_extract(
            url=binary_meta.url,
            internal_filepath=binary_meta.internal_filepath,
            hash_sha256=binary_meta.hash_sha256,
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
        cls, categories: LegalTermsCategory | LegalTermsCategoryCollection = LegalTermsCategory.ALL
    ) -> LegalTermsCollection:
        """Get legal terms for Ookla Speedtest.

        Args:
            categories: Category(s) of terms to retrieve. Defaults to ALL.

        Returns:
            Collection of legal terms that match the requested category.
        """
        # Return the terms collection filtered by the requested category
        if categories == LegalTermsCategory.ALL or LegalTermsCategory.ALL in categories:
            return cls._TERMS_COLLECTION
        return [term for term in cls._TERMS_COLLECTION if term.category in categories]

    def _parse_version(self) -> Version:
        """Get the version of the speedtest CLI as a Version object."""
        try:
            result = self._run_speedtest(["--version"], parse_json=False).get("stdout", "")
        except RuntimeError as e:
            # If the command fails, we can't determine the version
            raise InvalidVersion(f"Speedtest cli failure: {e}") from e

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
                    raw=server,
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

        # Extract server information
        server_data = result.get("server")
        server_info = (
            None
            if not server_data
            else ServerInfo(
                name=server_data.get("name"),
                id=server_data.get("id"),
                location=server_data.get("location"),
                country=server_data.get("country"),
                host=server_data.get("host"),
                raw=server_data,
            )
        )

        # Get download/upload data
        download_data = result.get("download", {})
        upload_data = result.get("upload", {})

        # Get download and upload bandwidth in bytes per second
        download_bytes_per_sec = download_data.get("bandwidth", None)
        upload_bytes_per_sec = upload_data.get("bandwidth", None)
        if download_bytes_per_sec is None or upload_bytes_per_sec is None:
            raise KeyError("Download or upload bandwidth missing from Ookla result")

        # Extract download and upload latency
        download_latency_ms = download_data.get("latency", {}).get("iqm", None)
        upload_latency_ms = upload_data.get("latency", {}).get("iqm", None)

        # Extract ping metrics
        ping_latency_ms = result.get("ping", {}).get("latency", None)
        ping_jitter_ms = result.get("ping", {}).get("jitter", None)

        # Extract packet loss percentage
        packet_loss = result.get("packetLoss", None)

        # Extract result ID and persist URL if available
        result_data = result.get("result", {})
        result_id = result_data.get("id", None)
        persist_url = result_data.get("url", None) if result_data.get("persisted", False) else None

        # Convert to timedeltas
        return MeasurementResult(
            download_speed=DataRateMbps(download_bytes_per_sec * 8 / 1_000_000),
            upload_speed=DataRateMbps(upload_bytes_per_sec * 8 / 1_000_000),
            download_latency=None
            if download_latency_ms is None
            else TimeDuration(milliseconds=download_latency_ms),
            upload_latency=None
            if upload_latency_ms is None
            else TimeDuration(milliseconds=upload_latency_ms),
            ping_latency=None
            if ping_latency_ms is None
            else TimeDuration(milliseconds=ping_latency_ms),
            ping_jitter=None
            if ping_jitter_ms is None
            else TimeDuration(milliseconds=ping_jitter_ms),
            packet_loss=None if packet_loss is None else Percentage(packet_loss),
            server_info=server_info,
            persist_url=persist_url,
            id=result_id,
            raw=result,
        )


# Register this provider
register_provider("ookla", OoklaProvider)
register_provider("speedtest", OoklaProvider)  # Alias
