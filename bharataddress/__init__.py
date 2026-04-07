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
from . import batch, digipin, enrichment, formatter, geocoder, similarity, validator
from .batch import parse_batch, parse_csv, parse_dataframe
from .enrichment import extract_state_from_gstin
from .formatter import format
from .geocoder import geocode, reverse_geocode
from .parser import ParsedAddress, parse
from .similarity import similarity as address_similarity
from .validator import is_deliverable, validate

__all__ = [
    "parse",
    "ParsedAddress",
    "digipin",
    "formatter",
    "format",
    "validator",
    "validate",
    "is_deliverable",
    "geocoder",
    "geocode",
    "reverse_geocode",
    "similarity",
    "address_similarity",
    "batch",
    "parse_batch",
    "parse_csv",
    "parse_dataframe",
    "enrichment",
    "extract_state_from_gstin",
    "__version__",
]
__version__ = "0.2.2"
