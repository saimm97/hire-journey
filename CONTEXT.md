# Hire Journey

Hire Journey helps job seekers maintain a career profile and discover relevant
opportunities from a shared catalog of public job postings.

## Job ingestion

**Ingestion Run**:
One attempt to fetch and persist jobs from every company feed selected for
ingestion.
_Avoid_: User search, recommendation run

**Ingestion Run Report**:
The internal operational record of one Ingestion Run's outcome, including its
overall status, Provider Ingestion Health, and safe issues. It is intended for
Hire Journey operators and automation, never job seekers.
_Avoid_: User report, search result

**Completed with Errors**:
An Ingestion Run outcome in which usable results were committed but one or more
company-level problems require operator attention. It is neither a complete
success nor a rolled-back or wholly failed run.
_Avoid_: Failed run, successful run

**Provider Ingestion Health**:
The aggregate outcome of the selected company feeds associated with one ATS
provider during an Ingestion Run. It measures Hire Journey's ingestion results,
not the availability or reliability of the provider's platform as a whole.
_Avoid_: Provider uptime, ATS status

**Degraded**:
A Provider Ingestion Health state in which at least one selected feed succeeded
and at least one failed. Issue codes describe the causes and severity of those
failures separately.
_Avoid_: Provider outage
