"""Deterministic project extraction from CV / projects-PDF text.

Projects are split primarily on blank lines — the most reliable record
separator. A block that starts with a bullet, link, or "Tech:" line can't be a
new project, so it's merged back into the one above. When a section has no blank
lines at all (a single block), a header heuristic splits it: a non-bullet,
non-meta line that follows some detail starts the next project.

Each project's name comes from its header (separators, parentheticals, and URLs
stripped); its points from the body; its tech stack from a "Tech:" line, a header
separator, or a parenthetical; its links from any URLs in the block. All regular
expressions live in :mod:`app.utils.patterns`.
"""

from app.schemas.project import ParsedProject
from app.utils import parsing, patterns


def extract_projects(text: str, *, section_only: bool = True) -> list[ParsedProject]:
    """Parse projects from ``text``.

    With ``section_only`` (CV), only the projects section is read. Without it
    (a projects-only PDF), the whole document is treated as the projects list
    when no section heading is present.
    """
    block_text = parsing.section_block(text, parsing.PROJECT_HEADINGS)
    if not block_text.strip() and not section_only:
        block_text = text
    if not block_text.strip():
        return []
    return [_build(group) for group in _grouped(block_text)]


def _grouped(block_text: str) -> list[dict]:
    blocks = _merge_continuations(parsing.blocks_of(block_text))
    if len(blocks) <= 1:
        return _group_by_header(blocks[0] if blocks else [])
    return [{"header": block[0], "body": block[1:]} for block in blocks]


def _merge_continuations(blocks: list[list[str]]) -> list[list[str]]:
    """Fold a block whose first line can't be a header into the block above."""
    merged: list[list[str]] = []
    for block in blocks:
        if merged and _is_continuation(block[0]):
            merged[-1].extend(block)
        else:
            merged.append(list(block))
    return merged


def _is_continuation(line: str) -> bool:
    return bool(patterns.BULLET_RE.match(line)) or _is_meta(line)


def _is_meta(line: str) -> bool:
    return bool(patterns.LINK_LINE_RE.match(line)) or bool(patterns.TECH_LABEL_RE.match(line))


def _group_by_header(lines: list[str]) -> list[dict]:
    groups: list[dict] = []
    current: dict | None = None
    seen_detail = False
    for line in lines:
        is_bullet = bool(patterns.BULLET_RE.match(line))
        if not is_bullet and not _is_meta(line) and (current is None or seen_detail):
            current = {"header": line, "body": []}
            groups.append(current)
            seen_detail = False
        elif current is not None:
            current["body"].append(line)
            seen_detail = seen_detail or is_bullet
    return groups


def _build(group: dict) -> ParsedProject:
    header, body = group["header"], group["body"]
    blob = " ".join([header, *body])

    tech, points = [], []
    for line in body:
        clean = patterns.BULLET_RE.sub("", line).strip()
        if patterns.TECH_LABEL_RE.match(clean):
            tech = parsing.parse_skills([patterns.TECH_LABEL_RE.sub("", clean)])
        elif clean and not patterns.LINK_LINE_RE.match(clean):
            points.append(clean)

    return ParsedProject(
        name=_name(header),
        summary="\n".join(points) or None,
        tech_stack=tech or _header_tech(header),
        github_url=parsing.normalize_url(parsing.re_first(patterns.GITHUB_RE, blob)),
        deployed_url=_deployed(blob),
    )


def _name(header: str) -> str:
    name = patterns.NAME_SPLIT_RE.split(header)[0]
    name = patterns.PAREN_RE.sub("", name)
    name = patterns.URL_RE.sub("", name).strip(" .|-–—")
    return name or header.strip()


def _header_tech(header: str) -> list[str]:
    parts = patterns.NAME_SPLIT_RE.split(header, maxsplit=1)
    if len(parts) > 1:
        return parsing.parse_skills([parts[1]])
    match = patterns.PAREN_RE.search(header)
    return parsing.parse_skills([match.group(1)]) if match else []


def _deployed(blob: str) -> str | None:
    for url in patterns.URL_RE.findall(blob):
        if "github.com" not in url.lower() and "linkedin.com" not in url.lower():
            return url.rstrip(".,)")
    return None
