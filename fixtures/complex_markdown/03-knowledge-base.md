#Knowledge Base: Troubleshooting Conversion

## FAQ

### Why does PDF fail on a fresh machine?

Because Pandoc requires an external PDF engine and that engine is not installed.

### Why does my heading layout look inconsistent?

Some files use headings without space after `#`, e.g. `##Title`.

### Why are some links broken?

Links like `www.site.local` can fail without a protocol.

## Troubleshooting Matrix

| Symptom | Possible Cause | Action |
|:--|:--|:--|
| `ModuleNotFoundError: yaml` | deps not installed | `pip install -e .[dev,ui]` |
| PDF output missing | no engine in PATH | install `wkhtmltopdf` |
| Empty history tab | no conversions yet | run one conversion |

## Bash Example

````bash
python -m app.main convert \
  --input fixtures/complex_markdown/03-knowledge-base.md \
  --profile configs/profiles/default.yaml
````

## Important Links

- Team runbook: [Runbook](www.runbook.local/main)
- Product docs: [User Guide](https://example.org/docs/user-guide)

## Checklist

- [ ] validate precheck output
- [ ] validate html render
- [ ] validate pdf render
- [ ] validate history row creation
