# argparse validation

This module builds on the basics and focuses on validating command-line input with Python's standard-library `argparse`.

## Covered patterns

- `type=` for conversion and validation,
- `choices=` for a closed set of accepted values,
- `required=True` for mandatory optional arguments,
- default values,
- reusable custom validators,
- `pathlib.Path` for filesystem-oriented CLI arguments.

## Requirements

- Python 3.9+
- no third-party packages

## Example

Create a small test file first:

```bash
echo "example" > report.csv
```

Then run:

```bash
python cli_validation.py report.csv --format csv
python cli_validation.py report.csv --format json --limit 50
python cli_validation.py report.csv --format csv --mode strict --output cleaned.csv
```

Show help:

```bash
python cli_validation.py --help
```

Invalid values are rejected before the main program logic runs. For example:

```bash
python cli_validation.py report.csv --format xml
```

produces an argparse error because `xml` is not one of the accepted choices.

Likewise:

```bash
python cli_validation.py report.csv --format csv --limit 0
```

fails because the custom `positive_int` validator accepts only values greater than zero.

## Design note

Keeping validation close to argument parsing makes the rest of the program simpler. After `parse_args()` succeeds, the application can assume that basic CLI constraints have already been checked.
