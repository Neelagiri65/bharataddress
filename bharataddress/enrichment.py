"""Enrichment helpers — derive address fields from non-address sources.

Currently:

- ``extract_state_from_gstin(gstin)`` — the first two digits of a GSTIN are
  the state code as defined by the GST Council. Returns the state name or
  ``None`` if the GSTIN is malformed or the code is unknown.

The lookup table is the official GST state code list. Pure data, no network.
"""
from __future__ import annotations

import re

# Source: GST Council state code list (TIN / state code).
GSTIN_STATE_CODES: dict[str, str] = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "25": "Daman and Diu",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "28": "Andhra Pradesh",  # pre-bifurcation; new registrations use 37
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman and Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
    "97": "Other Territory",
    "99": "Centre Jurisdiction",
}

_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")


def extract_state_from_gstin(gstin: str) -> str | None:
    """Return the state name encoded in the first two digits of a GSTIN.

    Returns ``None`` if the GSTIN is empty, malformed, or the code is unknown.
    Validation is structural (15-char GSTIN format); checksum is not verified.
    """
    if not isinstance(gstin, str) or not gstin:
        return None
    s = gstin.strip().upper()
    if not _GSTIN_RE.match(s):
        return None
    return GSTIN_STATE_CODES.get(s[:2])
