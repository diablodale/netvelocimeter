# NetVelocimeter

A Python library for measuring network performance metrics like bandwidth, latency, and ping times across multiple service providers.

## Installation

```bash
pip install netvelocimeter
```

## Usage

```python
from netvelocimeter import NetVelocimeter

# Use the default Ookla provider
nv = NetVelocimeter()

# Run a complete measurement
result = nv.measure()
print(f"Download: {result.download_speed:.2f} Mbps")
print(f"Upload: {result.upload_speed:.2f} Mbps")
print(f"Latency: {result.latency:.2f} ms")

# Or measure individual components
download_speed = nv.measure_download()
upload_speed = nv.measure_upload()
latency = nv.measure_latency()
```

## Supported Providers

- **Ookla/Speedtest.net**: Uses the official Ookla CLI tool

## Custom Binary Directory

By default, NetVelocimeter stores provider binaries in `~/.netvelocimeter/bin/`. You can specify a custom directory:

```python
nv = NetVelocimeter(binary_dir="/path/to/custom/directory")
```

## License

MIT
