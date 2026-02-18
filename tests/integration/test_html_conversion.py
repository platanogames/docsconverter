from pathlib import Path

import pytest

from app.core.config import load_profile
from app.core.models import ConversionJob
from app.core.pipeline import run_conversion_job


def test_html_conversion() -> None:
    pandoc = Path("pandoc-3.9-windows-x86_64/pandoc-3.9/pandoc.exe")
    if not pandoc.exists():
        pytest.skip("Pandoc local no encontrado")

    workdir = Path("build/test-artifacts/html-integration")
    workdir.mkdir(parents=True, exist_ok=True)
    input_md = workdir / "input.md"
    input_md.write_text("#Titulo\nContenido", encoding="utf-8")

    profile = load_profile(Path("configs/profiles/default.yaml"))
    html_output = workdir / "out.html"
    profile.outputs = [item for item in profile.outputs if item.format == "html"]
    profile.outputs[0].output_path = html_output

    job = ConversionJob(
        input_path=input_md,
        outputs=profile.outputs,
        style_profile=profile.style_profile,
        rules=profile.rules,
        build_dir=workdir / "build",
    )

    results = run_conversion_job(job, pandoc_path=pandoc, history_path=workdir / "history.jsonl")
    assert results[0].return_code == 0
    assert html_output.exists()
