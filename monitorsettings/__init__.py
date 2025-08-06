"""
Monitor Settings Control Package

A Python package for controlling monitor settings via DDC/CI protocol.
Currently supports brightness control with plans for additional settings.
"""

__version__ = "2.0.0"
__author__ = "Nick Knowles"

from .cli import main

__all__ = ["main", "__version__"]
