from __future__ import annotations
import pandas as pd

def deduplicate_inventory(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["hostname_norm"] = work["hostname"].astype(str).str.strip().str.lower()
    work["serial_norm"] = work["serial"].fillna("").astype(str).str.strip().str.upper()

    # Serial is stronger evidence than IP; hostname is the fallback.
    work["identity_key"] = work["serial_norm"].where(
        work["serial_norm"].ne(""),
        "HOST:" + work["hostname_norm"],
    )
    work = work.sort_values("observed_at")
    return work.drop_duplicates("identity_key", keep="last")

if __name__ == "__main__":
    sample = pd.DataFrame([
        {"hostname":"PC-01","serial":"ABC123","observed_at":"2026-09-01"},
        {"hostname":"pc-01","serial":"ABC123","observed_at":"2026-09-28"},
    ])
    print(deduplicate_inventory(sample).to_string(index=False))
