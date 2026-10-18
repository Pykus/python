# Reliable event reporting across daylight-saving changes with Pandas

Operational reports frequently combine events from monitoring systems, web applications, task schedulers and security logs. An event timestamp is not merely a formatted date: it identifies an instant. Confusing that instant with a local wall-clock reading produces duplicate or missing hourly buckets, misleading incident timelines and false SLA calculations. This chapter develops a reproducible Pandas workflow for Poland's `Europe/Warsaw` timezone, including both daylight-saving transitions.

## What problem does this solve?

During the autumn change from summer time to standard time, the hour from 02:00 to 02:59 occurs **twice**. On 25 October 2026, 02:30 with offset +02:00 and 02:30 with offset +01:00 represent different instants, separated by one hour. During the spring change, some local times never occur: on 29 March 2026, the clock jumps from 01:59 to 03:00. A report that strips timezone offsets cannot distinguish the autumn events and may invent events in the nonexistent spring hour.

This matters for a Zabbix/Wazuh incident timeline, a school server audit, scheduled task evidence, website traffic reports, billing windows and on-call duty summaries. Keep original instants in UTC, then convert for human presentation. Use UTC for elapsed-time arithmetic and fixed-duration hourly buckets; use the business timezone when a requirement explicitly concerns a local calendar day.

## When to use this approach — and when not

Use it when events arrive from multiple services, are compared across machines, must survive daylight-saving transitions, or feed an audit trail. Store ISO 8601 timestamps with `Z` or explicit numeric offsets; ideally include a stable event ID and source. Convert to local time only when building a user-facing report.

Do not apply a timezone conversion to timestamps that already represent unspecified local wall-clock times: first identify their originating timezone and whether an ambiguous time can be resolved. Do not assume `UTC+1` is Poland's year-round timezone. Avoid using `tz_localize` on already timezone-aware data: it is for attaching a timezone to naive readings, not converting instants. For purely date-based business records, a date field may be more appropriate than a timestamp.

## A complete, runnable report

Requirements: Python 3.11+ and Pandas 2.2+ (`python -m pip install "pandas>=2.2,<3"`). Save the following as `event_report.py` and run `python event_report.py`. No network or external data is needed.

```python
from __future__ import annotations

import pandas as pd

ZONE = "Europe/Warsaw"

EVENTS = [
    {"id": "autumn-a", "source": "zabbix", "occurred_at": "2026-10-25T00:30:00Z"},
    {"id": "autumn-b", "source": "wazuh", "occurred_at": "2026-10-25T01:30:00Z"},
    {"id": "spring-a", "source": "zabbix", "occurred_at": "2026-03-29T00:30:00Z"},
    {"id": "spring-b", "source": "wazuh", "occurred_at": "2026-03-29T01:30:00Z"},
]


def build_report(records: list[dict[str, str]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    events = pd.DataFrame.from_records(records)
    if events.empty:
        raise ValueError("No events supplied")
    required = {"id", "source", "occurred_at"}
    if not required.issubset(events.columns):
        raise ValueError(f"Missing fields: {sorted(required - set(events.columns))}")
    if events["id"].isna().any() or events["id"].duplicated().any():
        raise ValueError("Event IDs must be present and unique")

    # utc=True correctly handles Z and explicit offsets in one input column.
    events["instant_utc"] = pd.to_datetime(
        events["occurred_at"], utc=True, errors="coerce"
    )
    if events["instant_utc"].isna().any():
        raise ValueError("Invalid event timestamp: reject rather than silently drop")
    events = events.sort_values(["instant_utc", "id"]).reset_index(drop=True)
    events["local_time"] = events["instant_utc"].dt.tz_convert(ZONE)
    # %z preserves the offset, distinguishing the two autumn 02:30 readings.
    events["local_label"] = events["local_time"].dt.strftime(
        "%Y-%m-%d %H:%M:%S %z"
    )
    events["local_date"] = events["local_time"].dt.date

    # Fixed 60-minute buckets are computed in UTC, then displayed locally.
    events["hour_utc"] = events["instant_utc"].dt.floor("h")
    hourly = (
        events.groupby("hour_utc", as_index=False)
        .agg(event_count=("id", "size"))
        .sort_values("hour_utc")
    )
    hourly["hour_local"] = hourly["hour_utc"].dt.tz_convert(ZONE)
    hourly["hour_label"] = hourly["hour_local"].dt.strftime("%Y-%m-%d %H:00 %z")
    return events, hourly


if __name__ == "__main__":
    events, hourly = build_report(EVENTS)
    print(events[["id", "source", "instant_utc", "local_label"]].to_string(index=False))
    print("\nHourly counts (unique UTC buckets):")
    print(hourly[["hour_label", "event_count"]].to_string(index=False))
    print("\nLocal calendar-day totals:")
    print(events.groupby("local_date")["id"].count().to_string())
```

The autumn events display as `2026-10-25 02:30:00 +0200` and `2026-10-25 02:30:00 +0100`; they occupy distinct hourly buckets. The spring events display as `01:30 +0100` and `03:30 +0200`; there is no 02:30 local timestamp. The report uses the IANA timezone database, not a hard-coded offset.

## Verification: tests that catch silent time errors

Create `test_event_report.py` next to the program and run `python -m unittest -v`. The test deliberately checks **instants and offsets**, not merely the appearance of a date string.

```python
import unittest

from event_report import EVENTS, build_report


class EventReportTests(unittest.TestCase):
    def test_autumn_repeated_hour_keeps_both_offsets(self):
        events, hourly = build_report(EVENTS)
        labels = events.set_index("id")["local_label"]
        self.assertEqual(labels["autumn-a"], "2026-10-25 02:30:00 +0200")
        self.assertEqual(labels["autumn-b"], "2026-10-25 02:30:00 +0100")
        autumn = hourly[hourly["hour_label"].str.startswith("2026-10-25")]
        self.assertEqual(len(autumn), 2)
        self.assertEqual(autumn["event_count"].sum(), 2)

    def test_spring_skips_nonexistent_hour(self):
        events, _ = build_report(EVENTS)
        labels = events.set_index("id")["local_label"]
        self.assertEqual(labels["spring-a"], "2026-03-29 01:30:00 +0100")
        self.assertEqual(labels["spring-b"], "2026-03-29 03:30:00 +0200")

    def test_bad_timestamp_fails_closed(self):
        bad = [{"id": "broken", "source": "test", "occurred_at": "not-a-date"}]
        with self.assertRaises(ValueError):
            build_report(bad)

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            build_report([EVENTS[0], EVENTS[0]])


if __name__ == "__main__":
    unittest.main()
```

For an additional manual check, export `instant_utc`, `local_label`, `id` and `source` together. Never export only the local wall-clock label as an incident's unique time key. Compare row counts before and after transformations, and assert that UTC instants remain timezone-aware.

## Handling local-only input and mixed timestamp sources

If a legacy CSV contains `2026-10-25 02:30:00` with no offset, the timestamp alone is insufficient to tell which occurrence of 02:30 it means. Pandas can make that ambiguity explicit:

```python
import pandas as pd

naive = pd.DatetimeIndex(["2026-10-25 02:30:00"])
try:
    naive.tz_localize("Europe/Warsaw", ambiguous="raise")
except Exception as exc:
    print(type(exc).__name__, "— ask the source for an offset or UTC instant")
```

Similarly, a nonexistent spring time should be rejected rather than silently shifted when exact event chronology matters. In a migration where the source system provides an explicit DST flag, you may pass an appropriate `ambiguous` mask, but record how it was obtained. Do not infer it from event order without documented guarantees.

For local-day SLAs, define the calendar boundaries in `Europe/Warsaw` and convert those boundaries to UTC before filtering. A local day around the DST transition can contain 23 or 25 hours. Do not calculate a day's duration by assuming `24 * 3600` seconds. For elapsed durations, subtract timezone-aware UTC instants; for "same local date" reporting, group by the converted local date.

## Common mistakes and operational safeguards

**Mistake: removing offsets with `tz_localize(None)`.** This turns two different instants into the same naive 02:30. Keep UTC alongside any display string.

**Mistake: `tz_localize("Europe/Warsaw")` on UTC data.** This reinterprets UTC clock values as local wall time and shifts the underlying instant. For timezone-aware UTC data use `tz_convert`.

**Mistake: sorting by formatted local strings.** At the autumn transition, local clock order goes backward. Sort by the original UTC timestamp and use a stable ID as a tie-breaker.

**Mistake: grouping by a naive local hour.** The repeated hour collapses two distinct buckets. Bucket in UTC and convert the bucket labels for display.

**Mistake: silently accepting malformed timestamps.** `errors="coerce"` is useful for detecting invalid rows, but always check `isna()` and reject or quarantine them with evidence.

**Mistake: assuming every source clock is accurate.** UTC normalization cannot repair clock drift, missing timezone metadata or delayed ingestion. Preserve both event time and ingestion time when diagnosing distributed incidents; monitor NTP synchronization separately.

## Practical conclusions

The robust pattern is **ingest aware timestamps → normalize to UTC → validate IDs and timestamps → calculate durations/buckets in UTC → convert to the intended local timezone for presentation**. A local calendar day is a business grouping, not a guaranteed 24-hour interval. Tests around both DST boundaries are inexpensive and prevent misleading monitoring reports, incident timelines and scheduled-task audits. Keep the original UTC instant and offset-bearing local label in exported evidence so another administrator can independently reconstruct the event order.
