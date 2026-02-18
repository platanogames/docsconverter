from __future__ import annotations

import shutil
from pathlib import Path

from app.core.models import ConversionJob


def preflight_or_raise(job: ConversionJob, pandoc_path: Path) -> tuple[Path, str | None]:
    # Resolve pandoc
    resolved = pandoc_path
    if not resolved.exists():
        found = shutil.which("pandoc")
        if found:
            resolved = Path(found)
        else:
            raise RuntimeError(f"Pandoc no encontrado: {pandoc_path}")

    # Verify input
    if not job.input_path.exists():
        raise RuntimeError(f"Archivo de entrada no encontrado: {job.input_path}")

    # Ensure output directories exist
    for out in job.outputs:
        out.output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure build_dir exists
    if job.build_dir:
        job.build_dir.mkdir(parents=True, exist_ok=True)

    # Detect PDF engine if needed
    needs_pdf = any(out.format == "pdf" for out in job.outputs)
    detected_engine: str | None = None

    if needs_pdf:
        if job.style_profile.pdf_engine:
            detected_engine = job.style_profile.pdf_engine
        else:
            detected_engine = _detect_pdf_engine(job.style_profile.pdf_layout_mode)
            if detected_engine:
                job.style_profile.pdf_engine = detected_engine

        if not detected_engine:
            raise RuntimeError(
                "No se detecto motor PDF. Instala xelatex, pdflatex o wkhtmltopdf."
            )

    return resolved, detected_engine


def _detect_pdf_engine(pdf_layout_mode: str) -> str | None:
    if pdf_layout_mode == "native":
        for engine in ("xelatex", "pdflatex"):
            if shutil.which(engine):
                return engine
    else:
        # web mode
        for engine in ("wkhtmltopdf",):
            if shutil.which(engine):
                return engine
        # Also check native engines as fallback
        for engine in ("xelatex", "pdflatex"):
            if shutil.which(engine):
                return engine
    return None
