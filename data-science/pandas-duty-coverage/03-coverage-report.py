import pandas as pd

def coverage_report(assignments: pd.DataFrame, required: pd.DataFrame) -> pd.DataFrame:
    """Return required duty slots with assignment counts and coverage status."""
    keys = ["day", "break", "location"]
    counts = assignments.groupby(keys, dropna=False).size().rename("assigned").reset_index()
    report = required[keys].drop_duplicates().merge(counts, on=keys, how="left")
    report["assigned"] = report["assigned"].fillna(0).astype(int)
    report["status"] = report["assigned"].map(lambda n: "missing" if n == 0 else "covered")
    return report.sort_values(keys).reset_index(drop=True)
