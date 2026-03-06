"""services.name_utils

Shared name normalization utilities.

We use this to bridge:
- Sleeper IDs (string)
- NBA CDN IDs (numeric)
- BALLDONTLIE IDs (numeric)

Name matching is imperfect, but this normalization fixes most common issues:
- accents (Dončić -> doncic)
- punctuation / hyphens / apostrophes
- suffixes (Jr., Sr., II, III)
- extra whitespace
"""

from __future__ import annotations

import re
import unicodedata

_SUFFIXES = {
    "jr", "sr", "ii", "iii", "iv", "v",
}

_PUNCT_RE = re.compile(r"[^a-z0-9 ]+")

def normalize_player_name(name: str) -> str:
    if not name:
        return ""
    # Unicode normalize + strip accents
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()

    # Replace punctuation with spaces, then collapse
    s = s.replace("-", " ").replace("'", " ").replace(".", " ")
    s = _PUNCT_RE.sub(" ", s)

    parts = [p for p in s.split() if p]
    # Drop suffix if last token is a suffix
    if parts and parts[-1] in _SUFFIXES:
        parts = parts[:-1]
    return " ".join(parts)
