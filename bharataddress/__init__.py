"""bharataddress — deterministic Indian address parser.

Quick start:
    >>> from bharataddress import parse
    >>> result = parse("Flat 302, Raheja Atlantis, Near Hanuman Mandir, Sector 31, Gurgaon 122001")
    >>> result.pincode
    '122001'
    >>> result.state
    'Haryana'

DIGIPIN encode / decode:
    >>> from bharataddress import digipin
    >>> digipin.encode(28.6129, 77.2295)
    '39J-429-L4TK'
"""
from . import digipin
from .parser import ParsedAddress, parse

__all__ = ["parse", "ParsedAddress", "digipin", "__version__"]
__version__ = "0.1.5"
