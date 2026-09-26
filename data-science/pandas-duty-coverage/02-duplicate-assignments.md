# Pandas: detect duplicate duty assignments

Before optimizing a schedule, check whether the same person appears more than once in the same time slot. In pandas, `duplicated(["teacher", "slot"], keep=False)` returns all rows participating in such conflicts.

Treat this as an input data-quality check rather than a solver constraint. Sort the result by teacher and slot to make manual review easier.