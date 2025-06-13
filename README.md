# NetVelocimeter

Python library for measuring network performance metrics like bandwidth, latency, and jitter across multiple service providers.

## Installation

Use the [development setup](#setting-up-for-development). This is a work in progress and not yet ready for production use.

Eventually, I will publish to [PyPI](https://pypi.org/) and you will `pip install netvelocimeter`

## Requirements

- Python 3.10 or newer

## Features

<img align="right" src="netvelocimeter/assets/icons/netvelocimeter-128.png" alt="NetVelocimeter" width="128" height="128"/>

- Measure download speed, upload speed, latency, and jitter
- Support multiple network speed test providers with extensible architecture
- Server selection capabilities (auto or manual)
- Manage legal requirements (EULA, service terms, privacy policy, etc.)

## Supported Providers

- **Ookla Speedtest.net**: uses the official Ookla Speedtest CLI tool
- **Static**: usually for testing, does not require external dependencies or network

## Basic Usage

```python
from netvelocimeter import NetVelocimeter

# Create NetVelocimeter with the default Ookla provider
nv = NetVelocimeter(provider="ookla")

# Accept legal terms before running tests
nv.accept_terms(nv.legal_terms())

# Run a complete measurement
result = nv.measure()
print(f"Download: {result.download_speed:.2f} Mbps")
print(f"Upload: {result.upload_speed:.2f} Mbps")
print(f"Latency: {result.ping_latency.total_seconds() * 1000:.2f} ms")
print(f"Jitter: {result.ping_jitter.total_seconds() * 1000:.2f} ms")
print(f"Packet Loss: {result.packet_loss if result.packet_loss is not None else 'N/A'}")
if result.id:
    print(f"Measurement ID: {result.id}")
if result.persist_url:
    print(f"View results online: {result.persist_url}")
```

## Server Selection

List and select specific test servers:

```python
# Create NetVelocimeter instance, default is Ookla or specify a provider
nv = NetVelocimeter(provider="ookla")

# Accept terms before using
nv.accept_terms(nv.legal_terms())

# List available servers
servers = nv.servers
for server in servers:
    print(f"Server {server.name} in {server.location or 'unknown location'}")

# Run test with a specific server
result = nv.measure(server_id=12345)  # By server ID
# OR
result = nv.measure(server_host="speedtest.example.com")  # By hostname
```

## Provider Information

List information about providers:

```python
from netvelocimeter import list_providers, NetVelocimeter

# Get available provider information
providers = list_providers()
for provider in providers:
    print(f"{provider.name}:")
    for line in provider.description:
        print(f"  {line}")

# Get active provider name and version
nv = NetVelocimeter()
name = nv.name
version = nv.version
print(f"Provider: {name}, version: {version}")
```

## Legal Terms

NetVelocimeter provides a flexible system for handling legal terms from different providers.
Acceptance is persisted across sessions and invalidated if the terms change.
This is useful for providers that require users to accept terms before running tests.

```python
from netvelocimeter.terms import LegalTermsCategory

# Get all legal terms
terms = nv.legal_terms()

# Get terms by category
eula_terms = nv.legal_terms(categories=LegalTermsCategory.EULA)
service_terms = nv.legal_terms(categories=LegalTermsCategory.SERVICE)
privacy_terms = nv.legal_terms(categories=LegalTermsCategory.PRIVACY)

# Accept specific terms
nv.accept_terms(eula_terms)
nv.accept_terms(service_terms)
nv.accept_terms(privacy_terms)

# Or accept all terms at once
nv.accept_terms(nv.legal_terms())

# Check if specific terms are accepted
if nv.has_accepted_terms(eula_terms):
    print("EULA terms accepted!")

# Check if all terms are accepted
if nv.has_accepted_terms():
    print("All terms accepted!")
```

### Persistance of Legal Terms

Acceptance is stored as tiny JSON files uniquely named for each legal term by using
a cryptographic hash of the terms. Files are stored in default locations based on the operating system:

- Posix systems follow the "configuration files" rules from the
  [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec).
- Windows systems use the `%APPDATA%` directory. Some Python installations, e.g. from
  the Microsoft Store, may [transparently redirect](https://github.com/python/cpython/issues/84557)
  this to a [private per-user per-python-version location](https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-behind-the-scenes#file-system).

## Example with Error Handling

```python
from netvelocimeter import NetVelocimeter
from netvelocimeter.exceptions import LegalAcceptanceError
from datetime import timedelta

try:
    # Create the NetVelocimeter instance
    nv = NetVelocimeter(provider="ookla")

    # Accept all legal terms
    nv.accept_terms(nv.legal_terms())

    # Run the measurement
    result = nv.measure()

    print(f"Measurement ID: {result.id if result.id else 'N/A'}")
    print(f"Download: {result.download_speed:.2f} Mbps")
    print(f"Upload: {result.upload_speed:.2f} Mbps")
    print(f"Latency: {result.ping_latency.total_seconds() * 1000:.2f} ms")
    print(f"Jitter: {result.ping_jitter.total_seconds() * 1000:.2f} ms")
    print(f"Packet Loss: {result.packet_loss if result.packet_loss is not None else 'N/A'}")
    if result.persist_url:
        print(f"View results online: {result.persist_url}")

except LegalAcceptanceError as e:
    print(f"Legal acceptance error: {e}")
except Exception as e:
    print(f"Error running test: {e}")
```

## Command Line Interface (CLI)

NetVelocimeter provides a CLI for network measurement, server selection, provider info, and legal terms management.

### Usage

```bash
netvelocimeter [GLOBAL OPTIONS] COMMAND [ARGS]...

# Example:
netvelocimeter --provider ookla --format json measure run
```

#### Common Global Options

- `--format, -f FORMAT`     Output format: text, csv, tsv, json
- `--provider, -p NAME`     Service provider to use (e.g. ookla, static)
- `--help`                  Show help message, options, then exit

### Commands

For details on each command and its options, use `--help` after the command, e.g.:

```bash
netvelocimeter legal list --help
```

#### measure

- `measure run` Run a measurement with the selected provider.

#### server

- `server list` List available servers for the selected provider.

#### legal

- `legal accept` Accept legal terms (JSON only) from stdin for the selected provider.

- `legal list` List legal terms for the selected provider, optionally filtered by category.

- `legal status` Show acceptance status for legal terms for the selected provider, optionally filtered by category.

#### provider

- `provider list` List all available providers.

## Examples

Example scripts are provided in the `examples/` directory to demonstrate usage of the netvelocimeter library in real-world scenarios:

- `examples/basic_speed_test.py`: Minimal script to run a speed test using the default provider and print results.
- `examples/provider_selection.py`: Interactive script to list available providers, prompt the user to select one, display and accept legal terms, and run a speed test with the chosen provider.

To run an example, use one of the following approaches from the project root:

```bash
python -m examples.basic_speed_test
python -m examples.provider_selection
python -m examples.batch_automation
```

Or temporarily set the `PYTHONPATH` and run directly from the `examples/` directory:

```bash
cd examples
PYTHONPATH=.. python basic_speed_test.py
PYTHONPATH=.. python provider_selection.py
PYTHONPATH=.. python batch_automation.py
```

## Development

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen)](https://pre-commit.com/)
[![pytest](https://img.shields.io/badge/pytest-enabled-brightgreen)](https://docs.pytest.org/)
[![mypy](https://img.shields.io/badge/mypy-enabled-brightgreen)](http://mypy-lang.org/)
[![linter: ruff](https://img.shields.io/badge/linter-ruff-brightgreen.svg)](https://docs.astral.sh/ruff/)
[![style: ruff](https://img.shields.io/badge/style-ruff-brightgreen.svg)](https://docs.astral.sh/ruff/)

### Setting Up for Development

1. Clone the repository:

   ```bash
   git clone https://github.com/diablodale/netvelocimeter.git
   cd netvelocimeter
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:

   - On Windows:

     ```bat
     venv\Scripts\activate
     ```

   - On macOS and Linux:

     ```bash
     source venv/bin/activate
     ```

4. Install the development dependencies:

   ```bash
   pip install -e ".[dev]"
   ```

5. Install pre-commit hooks:

   ```bash
    pre-commit install
    ```

### Testing

Run the tests using `pytest`:

```bash
# Run all non-expensive tests (default)
pytest
```

To run tests with coverage:

```bash
pytest --cov=netvelocimeter
```

To see stdout and stderr during tests:

```bash
pytest -s
```

To run specific test files:

```bash
pytest tests/test_legal_requirements.py
```

For expensive tests, i.e. download binaries or make network requests:

```bash
# Run all tests including expensive ones
pytest --run-expensive

# Run only the expensive tests
pytest --run-only-expensive
```

When contributing new tests, use the `@pytest.mark.expensive` decorator for tests that:

- Download large files
- Make network requests
- Take a long time to run

Example:

```python
import pytest

@pytest.mark.expensive
def test_download_real_binary():
    # Test code that downloads real binaries
    ...
```

### Code Style

This project uses:

- mypy for type checking
- ruff for linting and style checking

Run the formatters and linters:

```bash
pre-commit run --all-files
```

### Documentation

~~Documentation is built with Sphinx. To build the docs:~~

```bash
# cd docs
# make html
```

~~Then open `docs/_build/html/index.html` in your browser.~~

### Creating a New Provider

#### Add To Netvelocimeter

1. Create a new py file in the `providers` directory for the provider
2. Implement a class that extends `BaseProvider` from base.py
3. Add tests for your provider in `tests` directory

#### Add To Your Own Project

1. Create a new py file in your project for the provider
2. Implement a class that extends `BaseProvider` from base.py
3. Register the provider in your project with `netvelocimeter.register_provider()`
4. Add tests for your provider in your project's test directory

### Building and Publishing

Build the package:

```bash
python -m build
```

Publish to PyPI:

```bash
python -m twine upload dist/*
```

### Contributing

Contributions are welcome! 😀👍🍰
[Please follow these steps.](CONTRIBUTING.md)

## License

Copyright 2025 Dale Phurrough

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

<http://www.apache.org/licenses/LICENSE-2.0>

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
