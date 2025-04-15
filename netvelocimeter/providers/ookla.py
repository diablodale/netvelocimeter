"""
Ookla Speedtest.net provider implementation.
"""

import json
import os
import platform
import subprocess
import sys
import zipfile
from typing import Dict, Optional, Tuple, List
import urllib.request
import shutil

from ..core import register_provider
from .base import BaseProvider, MeasurementResult
from ..utils.binary_manager import download_file, ensure_executable


class OoklaProvider(BaseProvider):
    """Provider for Ookla Speedtest.net."""

    _BINARY_NAME = "speedtest"
    _DOWNLOAD_URLS = {
        ("Windows", "AMD64"): "https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-win64.zip",
        ("Linux", "x86_64"): "https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-x86_64.tgz",
        ("Linux", "i386"): "https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-i386.tgz",
        ("Linux", "aarch64"): "https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-aarch64.tgz",
        ("Linux", "armel"): "https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-armel.tgz",
        ("Linux", "armhf"): "https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-armhf.tgz",
        ("Darwin", "x86_64"): "https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-macosx-universal.tgz",
        ("Darwin", "arm64"): "https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-macosx-universal.tgz",
        # https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-freebsd12-x86_64.pkg
        # https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-freebsd13-x86_64.pkg
    }

    def __init__(self, binary_dir: str):
        """
        Initialize the Ookla provider.

        Args:
            binary_dir: Directory to store the Ookla speedtest binary.
        """
        super().__init__(binary_dir)
        self.binary_path = self._ensure_binary()

    def _ensure_binary(self) -> str:
        """
        Ensure the Ookla speedtest binary is available.

        Returns:
            Path to the binary.
        """
        # e.g., Windows, Linux, Darwin; on iOS and Android returns the user-facing OS name (i.e, 'iOS, 'iPadOS' or 'Android')
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

        if system == "Windows":
            binary_filename = "speedtest.exe"
        else:
            binary_filename = "speedtest"

        binary_path = os.path.join(self.binary_dir, binary_filename)

        # Check if binary already exists
        if os.path.exists(binary_path):
            return binary_path

        # Download and extract
        download_url = self._DOWNLOAD_URLS[key]
        temp_file = os.path.join(self.binary_dir, os.path.basename(download_url))

        download_file(download_url, temp_file)

        try:
            # Extract based on file extension
            if download_url.endswith(".zip"):
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    zip_ref.extract(binary_filename, self.binary_dir)
            elif download_url.endswith(".tgz"):
                # For Linux .tgz files
                import tarfile
                with tarfile.open(temp_file, 'r:gz') as tar:
                    tar.extract(binary_filename, self.binary_dir)

            # Make binary executable
            ensure_executable(binary_path)

            return binary_path
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def _run_speedtest(self, args: List[str] = None) -> Dict:
        """
        Run the speedtest binary with the given arguments.

        Args:
            args: Additional arguments for the speedtest binary.

        Returns:
            Parsed JSON output from speedtest.
        """
        cmd = [self.binary_path, "--format=json", "--accept-license", "--accept-gdpr"]
        if args:
            cmd.extend(args)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Speedtest failed: {result.stderr}")

        return json.loads(result.stdout)

    def measure(self) -> MeasurementResult:
        """
        Run a complete speedtest.

        Returns:
            MeasurementResult with the test results.
        """
        result = self._run_speedtest()

        server_info = {
            "id": result.get("server", {}).get("id"),
            "name": result.get("server", {}).get("name"),
            "location": result.get("server", {}).get("location"),
            "host": result.get("server", {}).get("host"),
        }

        # Convert bits/s to Mbps (megabits per second)
        download_mbps = result.get("download", {}).get("bandwidth", 0) * 8 / 1_000_000
        upload_mbps = result.get("upload", {}).get("bandwidth", 0) * 8 / 1_000_000

        return MeasurementResult(
            download_speed=download_mbps,
            upload_speed=upload_mbps,
            latency=result.get("ping", {}).get("latency"),
            jitter=result.get("ping", {}).get("jitter"),
            packet_loss=result.get("packetLoss"),
            server_info=server_info,
            raw_result=result
        )

    def measure_download(self) -> float:
        """
        Measure download speed.

        Returns:
            Download speed in Mbps.
        """
        result = self._run_speedtest(["--no-upload"])
        return result.get("download", {}).get("bandwidth", 0) * 8 / 1_000_000

    def measure_upload(self) -> float:
        """
        Measure upload speed.

        Returns:
            Upload speed in Mbps.
        """
        result = self._run_speedtest(["--no-download"])
        return result.get("upload", {}).get("bandwidth", 0) * 8 / 1_000_000

    def measure_latency(self) -> float:
        """
        Measure network latency.

        Returns:
            Latency in ms.
        """
        result = self._run_speedtest(["--no-download", "--no-upload"])
        return result.get("ping", {}).get("latency")


# Register this provider
register_provider("ookla", OoklaProvider)
register_provider("speedtest", OoklaProvider)  # Alias
