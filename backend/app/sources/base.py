import re
from dataclasses import dataclass
from typing import Protocol

TIMEOUT = 10.0
_HTML_TAG = re.compile(r"<[^>]+>")


@dataclass
class RawJob:
    title: str
    url: str
    company: str
    location: str
    description: str = ""
    source_name: str = ""


class JobSource(Protocol):
    name: str

    async def fetch(self, company_slug: str, company_name: str) -> list[RawJob]:
        ...
