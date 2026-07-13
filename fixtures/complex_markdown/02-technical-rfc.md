#RFC-012 Conversion Pipeline Hardening

## Context

We need deterministic conversions across developer machines and CI agents.

## Goals

- Same markdown input should produce stable html output.
- PDF generation should fail with clear errors when engine is missing.
- Conversion metadata must be traceable.

## Non-Goals

- Real-time collaborative editing.
- Cloud synchronization.

## Proposed Architecture

### Layers

1. Presentation
2. Application
3. Domain
4. Infrastructure

### Sequence

1. Load profile.
2. Validate dependencies.
3. Apply rules.
4. Run Pandoc.
5. Persist history.

## Definition List

Pipeline
: Ordered set of processing steps.

Profile
: Serializable conversion settings.

## Nested Lists

- Inputs
  - markdown file
  - profile yaml
  - template assets
- Outputs
  - html artifact
  - pdf artifact
  - conversion history

## Table with Inline Code

| Component | Contract | Status |
|:--|:--|:--|
| RuleEngine | `apply(content) -> str` | stable |
| Converter | `convert(job)` | stable |
| UI | `run_ui()` | mvp |

## Code Fence Stress

````json
{
  "project_name": "RFC run",
  "outputs": [
    {"format": "html", "output_path": "build/rfc.html"},
    {"format": "pdf", "output_path": "build/rfc.pdf"}
  ]
}
````

## Link Sanitization Candidate

[Architecture Home](www.arch.local/docs)
