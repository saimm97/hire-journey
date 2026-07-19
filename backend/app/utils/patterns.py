"""Compiled regular expressions shared across the app.

Every pattern lives here so no expression is duplicated across files. Import
what you need: ``from app.utils import patterns`` then ``patterns.ISO_MONTH_RE``.
"""

import re

# Lenient date normalization for LLM-extracted resume dates
ISO_MONTH_RE = re.compile(r"^(\d{4})[-/](\d{1,2})$")
YEAR_ONLY_RE = re.compile(r"^(\d{4})$")
MONTH_NAME_RE = re.compile(r"^([A-Za-z]{3,9})\.?,?\s+(\d{4})$")
PRESENT_RE = re.compile(r"^(present|current|now|ongoing)$", re.I)

# Strict month format for user-edited payloads
STRICT_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# URL normalization: a schemeless value that still looks like a web address
DOMAIN_LIKE_RE = re.compile(r"^[\w-]+(?:\.[\w-]+)+(?:/\S*)?$")
