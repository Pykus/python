# Pandas merge validation

Make join cardinality assumptions executable with `validate`.

```python
result = assets.merge(users, on="user_id", how="left", validate="many_to_one")
```

If the supposedly unique side contains duplicates, Pandas raises instead of silently multiplying rows. Useful in inventory and reporting pipelines.
