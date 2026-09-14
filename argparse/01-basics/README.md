# argparse basics

A small, dependency-free introduction to Python's built-in `argparse` module.

## What this example covers

- creating an `ArgumentParser`,
- one positional argument (`name`),
- optional arguments with short and long forms,
- default values,
- a boolean flag with `store_true`,
- automatic `--help` output,
- a small validation function for a positive integer.

## Requirements

- Python 3.9+ recommended
- no third-party packages

## Run

From this directory:

```bash
python cli_basics.py Alice
python cli_basics.py Alice --greeting Hi
python cli_basics.py Alice --greeting Hi --times 3
python cli_basics.py Alice --uppercase
```

Show automatically generated help:

```bash
python cli_basics.py --help
```

Example output:

```text
$ python cli_basics.py Alice --greeting Hi --times 2
Hi, Alice!
Hi, Alice!
```

## Why use argparse?

For small scripts, manually reading `sys.argv` can work, but it quickly becomes difficult to maintain. `argparse` provides consistent parsing, generated help, defaults, flags, type conversion, and useful error messages using only the Python standard library.

## Next step

The next module expands this foundation with `type`, `choices`, required options, defaults, and validation patterns.
