param(
  [string]$Input = "samples/markdown/basic-report.md",
  [string]$Profile = "configs/profiles/default.yaml"
)

$ErrorActionPreference = "Stop"

Write-Host "== Smoke test DocsConverter =="

python -m app.main convert --input $Input --profile $Profile

if (Test-Path "build/output/report.html") {
  Write-Host "[ok] HTML generado: build/output/report.html"
} else {
  Write-Error "No se genero build/output/report.html"
}

if (Test-Path "build/output/report.pdf") {
  Write-Host "[ok] PDF generado: build/output/report.pdf"
} else {
  Write-Warning "No se genero PDF. Verifica motor PDF instalado."
}

if (Test-Path "logs/history.jsonl") {
  Write-Host "[ok] Historial generado: logs/history.jsonl"
} else {
  Write-Error "No se genero logs/history.jsonl"
}

Write-Host "Smoke test completado."
