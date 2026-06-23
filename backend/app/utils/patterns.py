"""Compiled regular expressions for document parsing.

Every pattern the extractors rely on lives here so the parsing modules stay
readable and no expression is duplicated across files. Import what you need:
``from app.utils import patterns`` then reference ``patterns.EMAIL_RE`` etc.
"""

import re

# Contact details
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|pub)/[\w%-]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w-]+(?:/[\w.-]+)?", re.I)
URL_RE = re.compile(r"https?://[^\s)\]]+", re.I)
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}")
NAME_RE = re.compile(r"^[A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3}$")

# Skills: collapse padded space runs to a delimiter, then split on separators.
WS_RUN_RE = re.compile(r"[ \t]{2,}")
SKILL_SPLIT_RE = re.compile(r"[,;|/]+|[•·▪◦]+")

# Projects
BULLET_RE = re.compile(r"^[•·▪◦\-–*]\s*")
TECH_LABEL_RE = re.compile(
    r"^(?:tech(?:nologies)?|tech stack|stack|built with|tools)\s*[:\-]\s*", re.I
)
LINK_LINE_RE = re.compile(
    r"^(?:https?://|www\.|[\w-]+\.(?:com|io|dev|org|net|app|co|ai))\S*$", re.I
)
NAME_SPLIT_RE = re.compile(r"\s[|–—-]\s")
PAREN_RE = re.compile(r"\((.*?)\)")
