# Inventory CLI with argparse

This example turns `argparse` subcommands into a small but useful inventory inspection tool rather than a parser-only snippet.

## What it is for

The CLI reads a JSON inventory export and supports three common administration tasks:

- `summary` — count devices and basic data-quality problems;
- `show HOSTNAME` — display one normalized device record;
- `audit` — find stale records and records missing a serial number.

It is useful as a pre-import check before feeding inventory data into another system, or as a small scheduled validation job.

## Input

The input file is a JSON array. Each item should contain `hostname`, `serial`, and `observed_at` in ISO-8601 format.

A synthetic example is included in `sample_inventory.json`.

## Usage

```bash
python inventory_cli.py --input sample_inventory.json summary
python inventory_cli.py --input sample_inventory.json show host-a
python inventory_cli.py --input sample_inventory.json audit --stale-days 30
python inventory_cli.py --input sample_inventory.json audit --stale-days 30 --json
```

Use `--now` to make audits deterministic in tests or automation:

```bash
python inventory_cli.py --input sample_inventory.json --now 2026-09-28T12:00:00Z audit --stale-days 30
```

## Exit codes

- `0` — command completed successfully;
- `2` — invalid input file or invalid record data;
- `3` — requested host was not found.

The tool is read-only. It never modifies the source inventory file.
