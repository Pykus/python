# Pandas: detect duplicate duty assignments

Before optimizing a schedule, it is worth checking whether the same person appears more than once in the same time slot. This is a data-quality problem that should be detected before the data reaches a solver or reporting layer.

## Example data

```python
import pandas as pd

assignments = pd.DataFrame(
    [
        {"teacher": "Teacher A", "slot": "Mon 08:00", "zone": "Hall A"},
        {"teacher": "Teacher A", "slot": "Mon 08:00", "zone": "Hall B"},
        {"teacher": "Teacher B", "slot": "Mon 08:00", "zone": "Hall C"},
        {"teacher": "Teacher C", "slot": "Mon 09:00", "zone": "Hall A"},
        {"teacher": "Teacher C", "slot": "Mon 09:00", "zone": "Hall A"},
    ]
)
```

## Find duplicate assignments

```python
duplicate_mask = assignments.duplicated(
    subset=["teacher", "slot"],
    keep=False,
)

conflicts = (
    assignments.loc[duplicate_mask]
    .sort_values(["teacher", "slot", "zone"])
    .reset_index(drop=True)
)

print(conflicts)
```

Example output:

```text
     teacher       slot    zone
0  Teacher A  Mon 08:00  Hall A
1  Teacher A  Mon 08:00  Hall B
2  Teacher C  Mon 09:00  Hall A
3  Teacher C  Mon 09:00  Hall A
```

## Distinguish duplicate rows from scheduling conflicts

Two rows can be identical because the source data was imported twice. A person assigned to two different zones in the same time slot is a different kind of problem.

```python
exact_duplicates = assignments[
    assignments.duplicated(keep=False)
].sort_values(["teacher", "slot", "zone"])

slot_conflicts = (
    assignments.groupby(["teacher", "slot"], as_index=False)
    .agg(
        assignment_count=("zone", "size"),
        unique_zones=("zone", "nunique"),
    )
    .query("assignment_count > 1")
)

print("Exact duplicate rows:")
print(exact_duplicates)

print("\nRepeated teacher/slot combinations:")
print(slot_conflicts)
```

This distinction matters: an exact duplicate can usually be removed with `drop_duplicates()`, while two different zones assigned to one teacher at the same time usually require a human decision or a scheduling rule.

## Optional cleanup

If exact duplicate rows are known to be accidental imports:

```python
cleaned = assignments.drop_duplicates().reset_index(drop=True)
```

Do not automatically remove rows merely because `teacher + slot` repeats. That could hide a real scheduling conflict.

## Reusable validation function

```python
def find_assignment_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    required = {"teacher", "slot", "zone"}
    missing = required.difference(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    duplicate_mask = df.duplicated(
        subset=["teacher", "slot"],
        keep=False,
    )

    return (
        df.loc[duplicate_mask]
        .sort_values(["teacher", "slot", "zone"])
        .reset_index(drop=True)
    )


conflicts = find_assignment_conflicts(assignments)

if conflicts.empty:
    print("No repeated teacher/slot assignments found.")
else:
    print(f"Found {len(conflicts)} conflicting rows:")
    print(conflicts)
```

## Why this check belongs before the solver

A solver should decide between valid alternatives. It should not have to compensate for accidental duplicate input rows or contradictory source assignments. Running a short pandas validation step first makes later optimization easier to debug and prevents bad source data from looking like an optimization failure.
