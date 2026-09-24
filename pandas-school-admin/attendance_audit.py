"""Small pandas tutorial: audit a school-journal CSV export.

Expected columns:
    class_code, lesson_date, subject, topic, attendance_status

Example:
    4A,2026-09-01,IT,Computer safety,present
    4A,2026-09-08,IT,,absent
    5B,2026-09-02,IT,Files and folders,

The script shows a practical data-quality workflow:
1. load CSV data,
2. normalize text and dates,
3. flag incomplete records,
4. aggregate problems by class,
5. optionally export rows that need review.

Use only anonymized/test exports when learning or publishing examples.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "class_code",
    "lesson_date",
    "subject",
    "topic",
    "attendance_status",
}


def load_journal(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    missing_columns = REQUIRED_COLUMNS.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()
    df["lesson_date"] = pd.to_datetime(df["lesson_date"], errors="coerce")

    for column in ("class_code", "subject", "topic", "attendance_status"):
        df[column] = df[column].fillna("").astype(str).str.strip()

    return df


def audit(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    reviewed = df.assign(
        missing_date=df["lesson_date"].isna(),
        missing_topic=df["topic"].eq(""),
        missing_attendance=df["attendance_status"].eq(""),
    )

    reviewed["needs_review"] = reviewed[
        ["missing_date", "missing_topic", "missing_attendance"]
    ].any(axis=1)

    summary = (
        reviewed.groupby("class_code", dropna=False)
        .agg(
            lessons=("class_code", "size"),
            rows_to_review=("needs_review", "sum"),
            missing_topics=("missing_topic", "sum"),
            missing_attendance=("missing_attendance", "sum"),
        )
        .sort_values(["rows_to_review", "class_code"], ascending=[False, True])
        .reset_index()
    )

    return reviewed, summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit an anonymized school-journal CSV export with pandas."
    )
    parser.add_argument("csv", type=Path, help="Path to the CSV export")
    parser.add_argument(
        "--problems-out",
        type=Path,
        help="Optional CSV path for rows that need review",
    )
    args = parser.parse_args()

    reviewed, summary = audit(load_journal(args.csv))

    print(summary.to_string(index=False))

    if args.problems_out:
        reviewed.loc[reviewed["needs_review"]].to_csv(
            args.problems_out,
            index=False,
        )
        print(f"Saved review queue to: {args.problems_out}")


if __name__ == "__main__":
    main()
