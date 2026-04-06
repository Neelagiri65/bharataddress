"""bharataddress — deterministic Indian address parser.

Quick start:
    >>> from bharataddress import parse
    >>> result = parse("Flat 302, Raheja Atlantis, Near Hanuman Mandir, Sector 31, Gurgaon 122001")
    >>> result.pincode
    '122001'
    >>> result.state
    'Haryana'
"""
from .parser import ParsedAddress, parse

__all__ = ["parse", "ParsedAddress", "__version__"]
__version__ = "0.1.0"
