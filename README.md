# NetVelocimeter

A Python library for measuring network performance metrics like bandwidth, latency, and jitter across multiple service providers.

## Installation

Use the [development setup](#setting-up-for-development). This is a work in progress and not yet ready for production use.

Eventually, I will publish to [PyPI](https://pypi.org/) and you will `pip install netvelocimeter`

## Requirements

- Python 3.10 or newer

## Features

<img align="right" src="netvelocimeter/assets/icons/netvelocimeter-128.png" alt="NetVelocimeter" width="128" height="128"/>

- Measure download speed, upload speed, latency, and jitter
- Support for multiple network speed test providers
- Server selection capabilities (auto or manual)
- Proper handling of legal requirements (EULA, terms, privacy policy)
- Type-safe time duration handling with `timedelta`
- Extensible architecture for adding new providers

## Basic Usage

```python
from netvelocimeter import NetVelocimeter

# Use the default Ookla provider with legal agreements acceptance
nv = NetVelocimeter(
    provider="ookla",
    accept_eula=True,
    accept_terms=True,
    accept_privacy=True
)

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

## Working with Legal Requirements

Some providers require acceptance of legal agreements:

```python
# Get legal requirements information
nv = NetVelocimeter(provider="ookla")
legal = nv.get_legal_requirements()

print(f"EULA URL: {legal.eula_url}")
print(f"Terms URL: {legal.terms_url}")
print(f"Privacy URL: {legal.privacy_url}")

# Check if legal requirements are met
if not nv.check_legal_requirements():
    print("Legal requirements must be accepted before running tests")
```

## Server Selection

List and select specific test servers:

```python
# List available servers
nv = NetVelocimeter(
    provider="ookla",
    accept_eula=True,
    accept_terms=True,
    accept_privacy=True
)

servers = nv.get_servers()
for server in servers:
    print(f"Server {server.name} in {server.location or 'unknown location'}")

# Run test with a specific server
result = nv.measure(server_id=12345)  # By server ID
# OR
result = nv.measure(server_host="speedtest.example.com")  # By hostname
```

## Provider Information

Get information about the provider:

```python
# Get provider version
nv = NetVelocimeter()
version = nv.get_provider_version()
print(f"Provider version: {version}")
```

## Custom Binary Directory

By default, NetVelocimeter stores provider binaries in `~/.netvelocimeter/bin/`. You can specify a custom directory:

```python
nv = NetVelocimeter(binary_dir="/path/to/custom/directory")
```

## Supported Providers

- **Ookla Speedtest.net**: uses the official Ookla Speedtest CLI tool

## Example with Error Handling

```python
from netvelocimeter import NetVelocimeter
from netvelocimeter.exceptions import LegalAcceptanceError
from datetime import timedelta

try:
    nv = NetVelocimeter(
        provider="ookla",
        accept_eula=True,
        accept_terms=True,
        accept_privacy=True
    )

    result = nv.measure()

    print(f"Measurement ID: {result.id if result.id else 'N/A'}")
    print(f"Download: {result.download_speed:.2f} Mbps")
    print(f"Upload: {result.upload_speed:.2f} Mbps")
    print(f"Latency: {result.ping_latency.total_seconds() * 1000:.2f} ms")
    print(f"Jitter: {result.ping_jitter.total_seconds() * 1000:.2f} ms")
    print(f"Packet Loss: {result.packet_loss if result.packet_loss is not None else 'N/A'}")
    if result.id:
        print(f"Measurement ID: {result.id}")
    if result.persist_url:
        print(f"View results online: {result.persist_url}")

except LegalAcceptanceError as e:
    print(f"Legal acceptance error: {e}")
except Exception as e:
    print(f"Error running test: {e}")
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

For tests that download binaries or make network requests:

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

~~Documentation is built with Sphinx. To build the docs:~~~~

```bash
# cd docs
# make html
```

~~Then open `docs/_build/html/index.html` in your browser.~~

### Creating a New Provider

To add support for a new speed test provider:

1. Create a new file in providers for your provider
2. Implement a class that extends `BaseProvider` from base.py
3. Register your provider in __init__.py
4. Add tests for your provider in tests

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

Contributions are welcome! 😀👍🍰 Please follow these steps:

1. Fork the repository
2. Create a new branch for your feature or bug fix
3. Implement your changes
4. Write tests for your changes
5. Ensure all tests pass
6. Submit a pull request

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
