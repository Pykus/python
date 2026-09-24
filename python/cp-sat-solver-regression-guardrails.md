# CP-SAT scheduling: regression guardrails before deployment

A scheduling solver can return a mathematically valid solution and still be a bad operational result. Before deploying a new CP-SAT configuration, run a small repeatable guardrail suite against a copy of production state.

This pattern is based on a real scheduling workflow, but uses neutral names and no environment-specific data.

## What to measure

At minimum, record:

- whether full coverage was found,
- number of missing assignments,
- coverage for each independent scheduling pool,
- runtime,
- a human-facing guardrail result,
- spillover from the preferred group,
- fairness deviation,
- solver status for critical phases,
- the seed/strategy used.

Do not compare versions using only objective value or only elapsed time.

## Example guardrail harness

```python
import json
import time
from pathlib import Path


def run_guardrails(solver, state, seeds=(0, 17, 41), max_seconds=90):
    report = {
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "checks": [],
        "failures": [],
    }

    # Phase 1: strict preferred-pool coverage.
    started = time.perf_counter()
    strict = solver.coverage(
        state,
        zone="preferred-zone",
        teachers=state["preferred_teachers"],
        allow_spillover=False,
        optimize=False,
    )
    wall = round(time.perf_counter() - started, 3)

    report["checks"].append({
        "name": "strict_preferred_pool",
        "wall_s": wall,
        "filled": strict["filled"],
        "missing": strict["missing"],
        "status": strict["status"],
        "spillover": strict.get("spillover", 0),
    })

    if strict["missing"] != 0:
        report["failures"].append("strict preferred pool is not full")

    if strict["status"] != "OPTIMAL":
        report["failures"].append("strict phase not proven OPTIMAL")

    # Phase 2: several quick-draft seeds.
    for seed in seeds:
        started = time.perf_counter()
        result = solver.quick_draft(
            state,
            seed=seed,
            optimize_seconds=4,
        )
        wall = round(time.perf_counter() - started, 3)

        report["checks"].append({
            "name": f"quick_seed_{seed}",
            "wall_s": wall,
            "full": result["full"],
            "missing": result["missing"],
            "coverage_primary": result["coverage_primary"],
            "coverage_secondary": result["coverage_secondary"],
            "human_ok": result["human_guardrail_ok"],
            "fairness_deviation": result["fairness_deviation"],
            "spillover": result.get("spillover", 0),
        })

        if not result["full"] or result["missing"] != 0:
            report["failures"].append(f"seed {seed}: incomplete")

        if not result["human_guardrail_ok"]:
            report["failures"].append(f"seed {seed}: human guardrail failed")

        if wall > max_seconds:
            report["failures"].append(f"seed {seed}: runtime above limit")

    report["ok"] = not report["failures"]
    report["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    return report
```

## Fail closed

A deployment candidate should fail the guardrail if any critical condition is worse than the production baseline. Typical hard failures are:

1. any missing assignment when production reaches zero,
2. a human-comfort rule becomes false,
3. unexpected spillover into a protected/preferred pool,
4. a critical CP-SAT phase is no longer proven optimal when that proof matters,
5. runtime exceeds the accepted ceiling,
6. fairness gets materially worse without an explicit trade-off.

## Save the report

Write a machine-readable report next to the test harness:

```python
report = run_guardrails(solver, state)

Path("solver-guardrails.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

raise SystemExit(0 if report["ok"] else 2)
```

A non-zero exit code makes the same test useful in a local deployment script or CI.

## Deployment rule

Do not deploy merely because one seed produced a complete schedule. Prefer:

- multiple representative seeds,
- a production-state copy,
- explicit regression thresholds,
- saved before/after reports,
- a rollback path,
- no production data mutation during the benchmark.

The strongest guardrail is simple: **a new solver version must be at least as complete and operationally acceptable as the version it replaces.**
