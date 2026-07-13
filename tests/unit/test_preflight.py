from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.models import ConversionJob, OutputTarget, StyleProfile
from app.core.preflight import preflight_or_raise


def _make_job(tmp_path: Path, formats: list[str], pdf_engine: str | None = None) -> ConversionJob:
    input_file = tmp_path / "input.md"
    input_file.write_text("# Test", encoding="utf-8")
    outputs = [OutputTarget(format=fmt, output_path=tmp_path / f"out.{fmt}") for fmt in formats]
    return ConversionJob(
        input_path=input_file,
        outputs=outputs,
        style_profile=StyleProfile(pdf_engine=pdf_engine),
    )


def test_preflight_resolves_bundled_pandoc(tmp_path: Path) -> None:
    pandoc = tmp_path / "pandoc.exe"
    pandoc.write_text("fake")
    job = _make_job(tmp_path, ["html"])
    resolved, engine = preflight_or_raise(job, pandoc)
    assert resolved == pandoc
    assert engine is None


def test_preflight_raises_when_pandoc_missing(tmp_path: Path) -> None:
    job = _make_job(tmp_path, ["html"])
    with patch("app.core.preflight.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="Pandoc no encontrado"):
            preflight_or_raise(job, tmp_path / "missing-pandoc.exe")


def test_preflight_raises_when_input_missing(tmp_path: Path) -> None:
    pandoc = tmp_path / "pandoc.exe"
    pandoc.write_text("fake")
    job = ConversionJob(
        input_path=tmp_path / "nonexistent.md",
        outputs=[OutputTarget(format="html", output_path=tmp_path / "out.html")],
    )
    with pytest.raises(RuntimeError, match="Archivo de entrada no encontrado"):
        preflight_or_raise(job, pandoc)


def test_preflight_raises_when_no_pdf_engine(tmp_path: Path) -> None:
    pandoc = tmp_path / "pandoc.exe"
    pandoc.write_text("fake")
    job = _make_job(tmp_path, ["pdf"])
    with patch("app.core.preflight.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="No se detecto motor PDF"):
            preflight_or_raise(job, pandoc)


def test_preflight_uses_configured_pdf_engine(tmp_path: Path) -> None:
    pandoc = tmp_path / "pandoc.exe"
    pandoc.write_text("fake")
    job = _make_job(tmp_path, ["pdf"], pdf_engine="xelatex")
    resolved, engine = preflight_or_raise(job, pandoc)
    assert engine == "xelatex"
