# Pandas merge validation: prevent silent row multiplication

A `merge()` can look correct while quietly producing too many rows. The usual cause is a wrong assumption about key uniqueness.

Use `validate=` to turn that assumption into an executable check.

## 1. many-to-one: many assets assigned to one user

This is a common inventory pattern:

```python
import pandas as pd

assets = pd.DataFrame(
    {
        "asset_id": ["PC-001", "PC-002", "PC-003", "PC-004"],
        "user_id": [10, 10, 11, 12],
        "model": ["Dell 7090", "HP 800 G6", "Lenovo M70", "Dell 7060"],
    }
)

users = pd.DataFrame(
    {
        "user_id": [10, 11, 12],
        "display_name": ["Anna Nowak", "Jan Kowalski", "Marta Zielinska"],
        "department": ["IT", "Office", "Finance"],
    }
)

result = assets.merge(
    users,
    on="user_id",
    how="left",
    validate="many_to_one",
)

print(result)
```

The left side may contain many rows for the same `user_id`, but the right side must contain exactly one row per user.

If `users` accidentally contains duplicate `user_id` values, Pandas raises `MergeError` instead of multiplying asset rows.

## 2. Diagnose duplicates before the merge

Do not wait for the merge to fail if you want a useful diagnostic report.

```python
duplicate_users = (
    users.loc[users.duplicated("user_id", keep=False)]
    .sort_values("user_id")
)

if not duplicate_users.empty:
    print("Duplicate user keys:")
    print(duplicate_users)
```

For several key columns:

```python
key = ["site", "device_name"]

duplicates = (
    inventory.loc[inventory.duplicated(key, keep=False)]
    .sort_values(key)
)
```

This is useful when the logical key is something like `site + hostname`, not a single ID.

## 3. one-to-one: both sides must be unique

Suppose one table contains one computer per asset tag and another contains exactly one warranty record per asset tag.

```python
computers = pd.DataFrame(
    {
        "asset_tag": ["A001", "A002", "A003"],
        "hostname": ["PC-01", "PC-02", "PC-03"],
    }
)

warranty = pd.DataFrame(
    {
        "asset_tag": ["A001", "A002", "A003"],
        "expires": ["2027-01-10", "2027-04-22", "2028-02-01"],
    }
)

merged = computers.merge(
    warranty,
    on="asset_tag",
    how="left",
    validate="one_to_one",
)
```

Use `one_to_one` when duplicates on either side indicate bad source data.

## 4. one-to-many: one master row expands into many detail rows

Example: one department has many devices.

```python
departments = pd.DataFrame(
    {
        "department_id": [1, 2],
        "department_name": ["Administration", "IT"],
    }
)

devices = pd.DataFrame(
    {
        "device_id": [101, 102, 103],
        "department_id": [1, 2, 2],
    }
)

result = departments.merge(
    devices,
    on="department_id",
    how="left",
    validate="one_to_many",
)
```

Here the left side must be unique by `department_id`; duplicates are allowed on the right.

## 5. many-to-many: allowed, but dangerous

Pandas also accepts:

```python
result = left.merge(
    right,
    on="key",
    validate="many_to_many",
)
```

This does not protect you from row multiplication. It only documents that duplicates are expected on both sides.

Example:

```python
left = pd.DataFrame(
    {
        "key": ["A", "A"],
        "left_value": [1, 2],
    }
)

right = pd.DataFrame(
    {
        "key": ["A", "A", "A"],
        "right_value": ["x", "y", "z"],
    }
)

result = left.merge(
    right,
    on="key",
    validate="many_to_many",
)

print(len(result))
# 6
```

Two rows matched three rows, so the result contains six rows.

That may be correct, but it should be intentional.

## 6. Audit row counts before and after the merge

A useful production check is to record counts around the join.

```python
before = len(assets)

result = assets.merge(
    users,
    on="user_id",
    how="left",
    validate="many_to_one",
)

after = len(result)

print(f"rows before: {before}")
print(f"rows after:  {after}")

if after != before:
    raise RuntimeError(
        f"Unexpected row-count change: {before} -> {after}"
    )
```

For a left join with a `many_to_one` relationship, the result should normally have the same number of rows as the left table.

## 7. Check unmatched rows with indicator=True

Cardinality validation does not tell you whether every key actually found a match.

Use `indicator=True`:

```python
result = assets.merge(
    users,
    on="user_id",
    how="left",
    validate="many_to_one",
    indicator=True,
)

unmatched = result.loc[result["_merge"] == "left_only"]

if not unmatched.empty:
    print("Assets without matching user:")
    print(unmatched[["asset_id", "user_id"]])
```

The `_merge` column contains:

- `both` — key matched on both sides,
- `left_only` — no matching row on the right,
- `right_only` — possible with right or outer joins.

## 8. Reusable helper for safer merges

For repeated ETL or reporting jobs, wrap the checks.

```python
from __future__ import annotations

import pandas as pd


def safe_left_merge(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    on: str | list[str],
    validate: str,
    require_all_matches: bool = False,
) -> pd.DataFrame:
    before = len(left)

    result = left.merge(
        right,
        on=on,
        how="left",
        validate=validate,
        indicator=True,
    )

    if len(result) != before:
        raise RuntimeError(
            f"Unexpected row-count change: {before} -> {len(result)}"
        )

    if require_all_matches:
        missing = result.loc[result["_merge"] == "left_only"]

        if not missing.empty:
            raise RuntimeError(
                f"{len(missing)} rows have no matching record"
            )

    return result.drop(columns="_merge")
```

Example:

```python
result = safe_left_merge(
    assets,
    users,
    on="user_id",
    validate="many_to_one",
    require_all_matches=True,
)
```

## 9. Practical audit pattern

A robust merge in an inventory or reporting pipeline often looks like this:

```python
key = "user_id"

duplicates = users.loc[
    users.duplicated(key, keep=False)
]

if not duplicates.empty:
    raise ValueError(
        "users contains duplicate user_id values:\n"
        + duplicates.to_string(index=False)
    )

result = assets.merge(
    users,
    on=key,
    how="left",
    validate="many_to_one",
    indicator=True,
)

missing_users = result.loc[
    result["_merge"] == "left_only",
    ["asset_id", "user_id"],
]

if not missing_users.empty:
    print("Warning: assets with no assigned user record")
    print(missing_users.to_string(index=False))

result = result.drop(columns="_merge")
```

This separates three different problems:

1. duplicate keys,
2. incorrect join cardinality,
3. missing matches.

They should not be treated as the same error.

## Quick reference

| Expected relationship | `validate=` |
| --- | --- |
| one row on each side | `"one_to_one"` |
| many left rows → one right row | `"many_to_one"` |
| one left row → many right rows | `"one_to_many"` |
| duplicates allowed on both sides | `"many_to_many"` |

The main rule: if you know what the relationship between the tables is supposed to be, encode it in `validate=` instead of relying on visual inspection of the merged output.
