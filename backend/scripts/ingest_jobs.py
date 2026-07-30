"""Run one globally locked ATS ingestion pass.

Intended for a deployment scheduler, for example twice daily:
    python scripts/ingest_jobs.py

The PostgreSQL advisory lock lives on a dedicated connection for the complete
run. If another scheduler or deployment is already ingesting, this process exits
without issuing ATS requests.
"""

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.services.ingestion_report import (
    IngestionIssue,
    IngestionRunFailedError,
    IngestionRunReport,
    RunStatus,
    report_to_dict,
)
from app.services.search_service import run_scan_locked
from app.sources.base import close_client


def render_json(report: IngestionRunReport) -> str:
    return json.dumps(report_to_dict(report), sort_keys=True)


def _format_duration(duration_ms: int) -> str:
    total_seconds = round(duration_ms / 1000)
    minutes, seconds = divmod(total_seconds, 60)
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _render_issues(title: str, issues: list[IngestionIssue]) -> list[str]:
    if not issues:
        return []
    grouped: dict[tuple[str, str], list[IngestionIssue]] = defaultdict(list)
    for issue in issues:
        grouped[(issue.provider or "unrouted", issue.code.value)].append(issue)

    lines = [f"{title}:"]
    for (provider, code), group in sorted(grouped.items()):
        lines.append(f"  {provider} / {code} ({len(group)})")
        for issue in group:
            subject = issue.company_name or "Run"
            lines.append(f"    - {subject}: {issue.message}")
            if issue.feed_url:
                lines.append(f"      feed: {issue.feed_url}")
    return lines


def render_human(report: IngestionRunReport) -> str:
    lines = [
        f"Run: {report.run_id}",
        f"Status: {report.status.value}",
        f"Duration: {_format_duration(report.duration_ms)}",
        (
            f"Companies: {report.companies_attempted} attempted, "
            f"{report.companies_succeeded} succeeded, "
            f"{report.companies_failed} failed, {report.empty_feeds} empty"
        ),
        f"Jobs: {report.jobs_fetched} fetched, {report.jobs_upserted} upserted",
    ]
    if report.providers:
        lines.extend(["", "Provider summary:"])
        for provider in report.providers:
            lines.append(
                f"  {provider.provider}: health={provider.ingestion_health.value}, "
                f"feeds={provider.feeds_attempted}, jobs={provider.jobs_fetched}, "
                f"feed_failures={provider.feeds_failed}, "
                f"persistence_failures={provider.persistence_failures}"
            )
    warning_lines = _render_issues("Warnings", report.warnings)
    error_lines = _render_issues("Errors", report.errors)
    if warning_lines:
        lines.extend(["", *warning_lines])
    if error_lines:
        lines.extend(["", *error_lines])
    return "\n".join(lines)


def exit_code_for(report: IngestionRunReport) -> int:
    return 0 if report.status in {RunStatus.COMPLETED, RunStatus.SKIPPED} else 1


async def run_command(*, json_output: bool = False) -> int:
    try:
        report = await run_scan_locked()
    except IngestionRunFailedError as exc:
        report = exc.report
    finally:
        await close_client()
    print(render_json(report) if json_output else render_human(report))
    return exit_code_for(report)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one globally locked ATS ingestion pass")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="print the complete structured run report as JSON",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_command(json_output=args.json_output)))


if __name__ == "__main__":
    main()
