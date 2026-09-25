# pandas: find duty coverage gaps

A synthetic example showing how to detect timetable slots with fewer assigned staff than required.

```python
import pandas as pd

coverage = pd.DataFrame({
    "slot": ["08:00", "08:10", "08:20", "08:30"],
    "required": [1, 2, 2, 1],
    "assigned": [1, 1, 2, 0],
})

coverage["missing"] = (coverage["required"] - coverage["assigned"]).clip(lower=0)
gaps = coverage.loc[coverage["missing"] > 0, ["slot", "required", "assigned", "missing"]]

print(gaps)
```

Expected gaps:

| slot | required | assigned | missing |
|---|---:|---:|---:|
| 08:10 | 2 | 1 | 1 |
| 08:30 | 1 | 0 | 1 |

## Extensions

- group by zone,
- calculate daily totals,
- compare planned vs actual coverage,
- export gaps to CSV,
- add a severity column based on `missing`.

The data is intentionally fictional and contains no real timetable or staff information.