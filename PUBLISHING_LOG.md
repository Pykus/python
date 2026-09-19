# Publishing log

This file tracks the public technical-material publishing queue so that each daily update is useful and non-duplicative.

| Date | Queue item | Path | Summary | Source type |
| --- | --- | --- | --- | --- |
| 2026-09-14 | 1. argparse basics | `argparse/01-basics/` | Introductory CLI example covering parser creation, positional and optional arguments, generated help, defaults, a boolean flag, and simple positive-integer validation. | `generated_fallback` |
| 2026-09-15 | 2. PowerShell environment locks | `powershell/environment-locks/` | Simplified workstation snapshot using native `pip freeze` and `winget export`; intentionally kept short instead of recreating package-manager functionality. | `sanitized_internal_example` |
| 2026-09-16 | 3. Python URL safety checker | `admin/url_safety_check.py` | Small standard-library checker extracted from an existing publishing workflow: rejects non-HTTPS, local and technical URLs before public publication. | `existing_worked_material` |
| 2026-09-17 | 4. URL expected-host validation | `admin/url_safety_check.py` | Extended the existing checker with the publisher's real host-matching pattern, so automation can require a domain such as `kahoot.com` while accepting its subdomains. | `existing_worked_material` |
| 2026-09-18 | 5. URL validation from stdin | `admin/url_safety_check.py` | Added one-URL-per-line stdin support so the same small checker can validate exported/generated link lists directly in shell pipelines without temporary argument expansion. | `existing_worked_material` |
| 2026-09-19 | 6. URL validation JSON output | `admin/url_safety_check.py` | Added optional JSON-lines output for feeding validation results into automation, logs or downstream Python without changing the default human-readable mode. | `existing_worked_material` |
| 2026-09-19 | 7. AZ-802 Drill scaffold + FSMO | `AZ-802-Drill/` | Added the public-safe AZ-802 learning area, topic backlog and first compact FSMO drill using fully anonymized lab identifiers. | `existing_worked_material` |
