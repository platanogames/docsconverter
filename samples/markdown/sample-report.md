# Sample Technical Report

## Introduction

This is a sample document to demonstrate DocsConverter's capabilities. It includes headings, lists, tables, code blocks, and links to showcase the full rendering pipeline.

## Architecture Overview

The system is composed of three main layers:

1. **Presentation Layer** — Desktop dashboard built with PySide6
2. **Core Engine** — Markdown processing, rule application, and Pandoc orchestration
3. **Configuration** — YAML-based profiles for reusable conversion settings

### Key Components

- Profile loader with path resolution
- Pre-flight validation and PDF engine auto-detection
- Style override generator for custom CSS injection
- JSONL-based conversion history

## Data Model

| Entity          | Type     | Description                        |
|-----------------|----------|------------------------------------|
| ConversionJob   | Pydantic | Input path, outputs, style, rules  |
| StyleProfile    | Pydantic | Templates, CSS, PDF engine config  |
| DocumentMetadata| Pydantic | Title, author, version, dates      |
| OutputTarget    | Pydantic | Format (html/pdf/docx) + path      |

## Code Example

```python
from app.core.models import ConversionJob, OutputTarget
from app.core.pipeline import run_conversion_job

job = ConversionJob(
    input_path=Path("doc.md"),
    outputs=[OutputTarget(format="html", output_path=Path("out.html"))],
)
results = run_conversion_job(job, pandoc_path=Path("pandoc"))
```

## Conclusion

DocsConverter simplifies the process of generating professional documents from Markdown sources. With YAML profiles and a visual dashboard, teams can standardize their document output across projects.

---

> For more information, visit the project repository.
