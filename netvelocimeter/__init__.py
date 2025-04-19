"""
NetVelocimeter - A Python library for measuring network performance.

This library provides a unified interface for measuring network performance metrics
such as bandwidth, latency, and ping times using various service providers.
"""

__version__ = "0.1.0"

from .core import NetVelocimeter, get_provider, list_providers, register_provider

__all__ = ["NetVelocimeter", "get_provider", "list_providers", "register_provider"]
