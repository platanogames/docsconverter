from pathlib import Path

import pytest

from app.core.config import load_profile
from app.core.models import ConversionJob, OutputTarget
from app.core.pipeline import run_conversion_job


def test_epub_conversion() -> None:
    pandoc = Path("pandoc-3.9-windows-x86_64/pandoc-3.9/pandoc.exe")
    if not pandoc.exists():
        pytest.skip("Pandoc local no encontrado")

    workdir = Path("build/test-artifacts/epub-integration")
    workdir.mkdir(parents=True, exist_ok=True)
    input_md = workdir / "input.md"
    input_md.write_text("# Titulo EPUB\n\nContenido para EPUB.", encoding="utf-8")

    profile = load_profile(Path("configs/profiles/default.yaml"))
    profile.outputs = [OutputTarget(format="epub", output_path=workdir / "out.epub")]

    job = ConversionJob(
        input_path=input_md,
        outputs=profile.outputs,
        style_profile=profile.style_profile,
        metadata=profile.metadata,
        rules=profile.rules,
        build_dir=workdir / "build",
    )

    results = run_conversion_job(job, pandoc_path=pandoc, history_path=workdir / "history.jsonl")
    assert results[0].return_code == 0
    assert (workdir / "out.epub").exists()
