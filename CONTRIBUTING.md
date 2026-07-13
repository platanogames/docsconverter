# Contributing to DocsConverter

Thanks for helping improve DocsConverter. Contributions should stay focused,
testable, and compatible with the supported Python and Pandoc workflows.

## Development setup

```bash
git clone https://github.com/platanogames/docsconverter.git
cd docsconverter
python -m venv .venv
```

Activate the environment, then install the project with development and UI
dependencies:

```bash
python -m pip install -e ".[dev,ux]"
```

Pandoc is an external runtime dependency. Install it separately and confirm
that `pandoc --version` works before testing conversions.

## Before opening a pull request

```bash
python -m ruff check --select F,I app tests
python -m pytest tests -v
```

- Keep changes small and explain the user-visible effect.
- Add or update tests for behavioral changes.
- Update `README.md` or `docs/` when commands, profiles, or output behavior change.
- Do not commit generated documents, local profiles, virtual environments, or
  Pandoc binaries.

## Reporting issues

Include the operating system, Python version, Pandoc version, command or UI
workflow used, expected result, actual result, and a minimal input document when
possible. Remove confidential content before attaching files.

## Commit and pull request style

Use a short imperative summary and provide verification evidence in the pull
request description. A maintainer may request a narrower change when unrelated
refactoring makes review harder.
