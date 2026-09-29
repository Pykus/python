# pandas: detect inventory changes between snapshots

For administrative inventories, compare stable identifiers rather than row order.

```python
import pandas as pd

old = pd.read_csv('inventory-old.csv').set_index('asset_id')
new = pd.read_csv('inventory-new.csv').set_index('asset_id')

added = new.index.difference(old.index)
removed = old.index.difference(new.index)
common = old.index.intersection(new.index)
changed = common[(old.loc[common] != new.loc[common]).any(axis=1)]

print('added', list(added))
print('removed', list(removed))
print('changed', list(changed))
```

This pattern is useful for GLPI/Zabbix-style inventory reconciliation because it separates identity from mutable attributes.