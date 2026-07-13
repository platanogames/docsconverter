# DocsConverter

[![CI](https://github.com/platanogames/docsconverter/actions/workflows/ci.yml/badge.svg)](https://github.com/platanogames/docsconverter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

A Python tool that converts Markdown documents into polished **HTML**, **PDF**, **DOCX**, and **EPUB** files using [Pandoc](https://pandoc.org/). Includes a PySide6 desktop dashboard for real-time style customization, metadata editing, batch processing, and sanitization.

> **Status:** Early development (v0.1.0). Core conversion pipeline is functional.

---

## Features

- **Multi-format output** — Convert `.md` to HTML, PDF, DOCX, and EPUB in a single run
- **YAML profiles** — Define reusable conversion configurations
- **UX Dashboard** — New tabbed interface for single/batch conversion, grouped metadata, and **Drag & Drop** support.
- **Style customization** — Live-preview dashboard with theme presets and typography controls
- **Markdown sanitization** — Rule-based cleanup before conversion
- **Quick Start** — New `run_dashboard.bat` for easy one-click launch on Windows.

## Quick Start

```bash
# Clone and install
git clone https://github.com/YOUR_USER/docsconverter.git
cd docsconverter

# Easy launch (Windows)
run_dashboard.bat
```

Download [Pandoc](https://pandoc.org/installing.html) and either:
- Install system-wide (auto-detected), or
- Place the binary at `pandoc-3.9-windows-x86_64/pandoc-3.9/pandoc.exe`

### CLI Usage

```bash
# Single file conversion
python -m app.main convert \
  --input samples/markdown/sample-report.md \
  --profile configs/profiles/default.yaml

# Batch conversion (entire directory)
python -m app.main convert-dir \
  --input-dir samples/markdown \
  --profile configs/profiles/default.yaml

# Launch desktop dashboard
python -m app.main ui
```

Converted files are written to `build/output/` by default (configurable per profile).

### PDF Modes

- **`web`** — Renders via `wkhtmltopdf`, maximizing visual parity with HTML output
- **`native`** — Renders via Pandoc + LaTeX (`xelatex`/`pdflatex`) for native PDF typesetting

If no `pdf_engine` is set in the profile, the tool auto-detects an available engine.

## Desktop Dashboard

Launch with `python -m app.main ui`. The dashboard provides:

- Visual profile editor with live HTML preview
- Style customization dialog (themes, colors, typography, table density)
- Document presets (Draft, Internal, Approved, Confidential)
- Batch conversion with progress bar and summary table
- Conversion history with metrics (total, success, errors)
- Sanitization panel for markdown cleanup before conversion

## Project Structure

```
docsconverter/
  app/
    core/
      models.py            Pydantic data models
      pipeline.py          Conversion engine (Pandoc subprocess)
      preflight.py         Validation and PDF engine detection
      rules.py             Markdown normalization
      sanitizer.py         Rule-based markdown cleanup
      sanitizer_config.py  Sanitization YAML loader
      style_builder.py     CSS override generator
      history.py           JSONL conversion log
      batch.py             Directory batch processing
      config.py            YAML profile loader/saver
    ui/
      window.py            PySide6 dashboard
    main.py                CLI entry point
  configs/
    profiles/              Conversion profiles (YAML)
    sanitization.yaml      Sanitization rules
  templates/
    base.html              Pandoc HTML template
  styles/
    report.css             Base document stylesheet
  samples/markdown/        Example markdown files
  tests/                   Unit and integration tests
```

## Profiles

Profiles are YAML files that bundle all conversion settings:

```yaml
project_name: My Report
outputs:
  - format: html
    output_path: build/output/report.html
  - format: pdf
    output_path: build/output/report.pdf
style_profile:
  pdf_layout_mode: web
  template_html: ../../templates/base.html
  css: ../../styles/report.css
  options:
    document_theme: light
    zebra_tables: true
    accent_color: '#0f766e'
metadata:
  title: My Report
  classification: internal
  language: es
rules:
  normalize_headings: true
  fix_code_fences: true
```

Built-in profiles: `default`, `auditoria`, `ue-audit`, `ue-architecture`.

## Tests

```bash
python -m pytest tests/ -v
```

## License

MIT. See [LICENSE](LICENSE).

## Contributing and security

- [Contribution guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Code of conduct](CODE_OF_CONDUCT.md)
