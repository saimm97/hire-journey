from dataclasses import dataclass
from typing import Protocol


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
