"""Deterministic project extraction from CV text.

Within the projects section, each project is a header line (its name) followed by
bullet/description lines (its points). A new non-bullet line after bullets starts
the next project — unless it's a link or a "Tech:" line, which belong to the
current project. Tech stack comes from a "Tech:" line, a header separator, or a
parenthetical; links from any URLs in the block.
"""

import re

from app.schemas.project import ParsedProject
from app.services.text_extract import (
    GITHUB_RE,
    PROJECT_HEADINGS,
    URL_RE,
    lines_of,
    normalize_url,
    parse_skills,
    section_lines,
)

_BULLET_RE = re.compile(r"^[•·▪◦\-–*]\s*")
_TECH_LABEL_RE = re.compile(
    r"^(?:tech(?:nologies)?|tech stack|stack|built with|tools)\s*[:\-]\s*", re.I
)
_LINK_LINE_RE = re.compile(
    r"^(?:https?://|www\.|[\w-]+\.(?:com|io|dev|org|net|app|co|ai))\S*$", re.I
)
_NAME_SPLIT_RE = re.compile(r"\s[|–—-]\s")


def extract_projects(text: str) -> list[ParsedProject]:
    return [_build(block) for block in _group(section_lines(lines_of(text), PROJECT_HEADINGS))]


def _is_meta(line: str) -> bool:
    return bool(_LINK_LINE_RE.match(line)) or bool(_TECH_LABEL_RE.match(line))


def _group(lines: list[str]) -> list[dict]:
    blocks: list[dict] = []
    current: dict | None = None
    seen_detail = False
    for line in lines:
        is_bullet = bool(_BULLET_RE.match(line))
        if not is_bullet and not _is_meta(line) and (current is None or seen_detail):
            current = {"header": line, "body": []}
            blocks.append(current)
            seen_detail = False
        elif current is not None:
            current["body"].append(line)
            seen_detail = seen_detail or is_bullet
    return blocks


def _build(block: dict) -> ParsedProject:
    header, body = block["header"], block["body"]
    blob = " ".join([header, *body])

    tech, points = [], []
    for line in body:
        clean = _BULLET_RE.sub("", line).strip()
        if _TECH_LABEL_RE.match(clean):
            tech = parse_skills([_TECH_LABEL_RE.sub("", clean)])
        elif clean and not _LINK_LINE_RE.match(clean):
            points.append(clean)

    return ParsedProject(
        name=_name(header),
        summary="\n".join(points) or None,
        tech_stack=tech or _header_tech(header),
        github_url=normalize_url(_first(GITHUB_RE, blob)),
        deployed_url=_deployed(blob),
    )


def _first(pattern: re.Pattern, text: str) -> str | None:
    found = pattern.search(text)
    return found.group(0) if found else None


def _name(header: str) -> str:
    name = _NAME_SPLIT_RE.split(header)[0]
    name = re.sub(r"\(.*?\)", "", name)
    name = URL_RE.sub("", name).strip(" .|-–—")
    return name or header.strip()


def _header_tech(header: str) -> list[str]:
    parts = _NAME_SPLIT_RE.split(header, maxsplit=1)
    if len(parts) > 1:
        return parse_skills([parts[1]])
    match = re.search(r"\((.*?)\)", header)
    return parse_skills([match.group(1)]) if match else []


def _deployed(blob: str) -> str | None:
    for url in URL_RE.findall(blob):
        if "github.com" not in url.lower() and "linkedin.com" not in url.lower():
            return url.rstrip(".,)")
    return None
