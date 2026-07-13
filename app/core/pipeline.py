from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.core.history import append_history
from app.core.models import ConversionJob, ConversionResult, OutputTarget
from app.core.paths import get_user_data_dir
from app.core.rules import apply_rules
from app.core.style_builder import build_override_css


def run_conversion_job(
    job: ConversionJob,
    pandoc_path: Path,
    history_path: Path,
    progress_callback: Callable[[int, str], None] | None = None,
    sanitization_config: object | None = None,
) -> list[ConversionResult]:
    results: list[ConversionResult] = []
    total = len(job.outputs)
    if total == 0:
        return results

    # Read and process input
    content = job.input_path.read_text(encoding="utf-8")

    # Apply sanitization if config provided
    if sanitization_config is not None:
        from app.core.sanitizer import MarkdownSanitizer, SanitizationConfig

        if isinstance(sanitization_config, SanitizationConfig):
            sanitizer = MarkdownSanitizer(sanitization_config)
            content, _stats = sanitizer.sanitize(content)

    # Apply markdown rules
    content = apply_rules(content, job.rules)

    # Prepare build directory
    build_dir = job.build_dir or get_user_data_dir() / "build" / "pipeline"
    build_dir.mkdir(parents=True, exist_ok=True)

    # Write processed markdown
    processed_md = build_dir / "processed.md"
    processed_md.write_text(content, encoding="utf-8")

    # Generate override CSS
    override_css_path = build_dir / "override.css"
    override_css = build_override_css(job.style_profile.options)
    override_css_path.write_text(override_css, encoding="utf-8")

    for idx, output in enumerate(job.outputs):
        pct_start = 10 + int((idx / total) * 80)
        pct_end = 10 + int(((idx + 1) / total) * 80)
        if progress_callback:
            progress_callback(pct_start, f"Convirtiendo {output.format.upper()}...")

        result = _convert_single(
            job=job,
            output=output,
            processed_md=processed_md,
            override_css_path=override_css_path,
            pandoc_path=pandoc_path,
            build_dir=build_dir,
        )
        results.append(result)

        # Record history
        append_history(
            history_path,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "format": output.format,
                "return_code": result.return_code,
                "output_path": str(output.output_path),
                "elapsed_seconds": result.elapsed_seconds,
                "timed_out": result.timed_out,
                "input_path": str(job.input_path),
            },
        )

        if progress_callback:
            progress_callback(pct_end, f"{output.format.upper()} completado.")

    return results


def _convert_single(
    job: ConversionJob,
    output: OutputTarget,
    processed_md: Path,
    override_css_path: Path,
    pandoc_path: Path,
    build_dir: Path,
) -> ConversionResult:
    output.output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [str(pandoc_path), str(processed_md), "-o", str(output.output_path), "--standalone"]

    # Add metadata variables
    meta = job.metadata
    if meta.title:
        cmd.extend(["-V", f"title={meta.title}"])
    if meta.subtitle:
        cmd.extend(["-V", f"subtitle={meta.subtitle}"])
    if meta.author:
        cmd.extend(["-V", f"author={meta.author}"])
    if meta.reviewer:
        cmd.extend(["-V", f"reviewer={meta.reviewer}"])
    if meta.version:
        cmd.extend(["-V", f"version={meta.version}"])
    if meta.classification:
        cmd.extend(["-V", f"classification={meta.classification}"])
    if meta.language:
        cmd.extend(["-V", f"lang={meta.language}"])
    if meta.date:
        cmd.extend(["-V", f"date={meta.date}"])
    if meta.header_left:
        cmd.extend(["-V", f"header_left={meta.header_left}"])
    if meta.header_center:
        cmd.extend(["-V", f"header_center={meta.header_center}"])
    if meta.header_right:
        cmd.extend(["-V", f"header_right={meta.header_right}"])
    if meta.footer_left:
        cmd.extend(["-V", f"footer_left={meta.footer_left}"])
    if meta.footer_center:
        cmd.extend(["-V", f"footer_center={meta.footer_center}"])
    if meta.footer_right:
        cmd.extend(["-V", f"footer_right={meta.footer_right}"])
    if meta.watermark:
        cmd.extend(["-V", f"watermark={meta.watermark}"])
    if meta.approver:
        cmd.extend(["-V", f"approver={meta.approver}"])
    if meta.approval_date:
        cmd.extend(["-V", f"approval_date={meta.approval_date}"])
    if meta.signatures_enabled:
        cmd.extend(["-V", "signatures_enabled=true"])

    # Table of contents
    cmd.append("--toc")

    # Format-specific options
    fmt = output.format.lower()

    if fmt == "html":
        if job.style_profile.template_html and job.style_profile.template_html.exists():
            cmd.extend(["--template", str(job.style_profile.template_html)])
        css_files: list[Path] = []
        if job.style_profile.css and job.style_profile.css.exists():
            css_files.append(job.style_profile.css)
        css_files.append(override_css_path)
        for css_path in css_files:
            cmd.extend(["--css", str(css_path)])

    elif fmt == "pdf":
        engine = job.style_profile.pdf_engine
        if engine and engine in ("xelatex", "pdflatex", "lualatex"):
            cmd.extend(["--pdf-engine", engine])
            if job.style_profile.latex_header and job.style_profile.latex_header.exists():
                cmd.extend(["-H", str(job.style_profile.latex_header)])
            if job.style_profile.template_pdf and job.style_profile.template_pdf.exists():
                cmd.extend(["--template", str(job.style_profile.template_pdf)])
        elif engine and "wkhtmltopdf" in engine:
            cmd.extend(["--pdf-engine", "wkhtmltopdf"])
            if job.style_profile.template_html and job.style_profile.template_html.exists():
                cmd.extend(["--template", str(job.style_profile.template_html)])
            css_files_pdf: list[Path] = []
            if job.style_profile.css and job.style_profile.css.exists():
                css_files_pdf.append(job.style_profile.css)
            css_files_pdf.append(override_css_path)
            for css_path in css_files_pdf:
                cmd.extend(["--css", str(css_path)])
        else:
            # Fallback: try as-is
            if engine:
                cmd.extend(["--pdf-engine", engine])

    elif fmt == "docx":
        # DOCX uses pandoc defaults; reference doc could be added later
        pass

    elif fmt == "epub":
        if job.style_profile.css and job.style_profile.css.exists():
            cmd.extend(["--css", str(job.style_profile.css)])
        cmd.extend(["--css", str(override_css_path)])

    # Execute
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        elapsed = time.monotonic() - start
        return ConversionResult(
            output=output,
            return_code=proc.returncode,
            elapsed_seconds=round(elapsed, 3),
            timed_out=False,
            stderr=proc.stderr,
            stdout=proc.stdout,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return ConversionResult(
            output=output,
            return_code=1,
            elapsed_seconds=round(elapsed, 3),
            timed_out=True,
            stderr="Conversion timed out after 120 seconds",
            stdout="",
        )
    except Exception as exc:
        elapsed = time.monotonic() - start
        return ConversionResult(
            output=output,
            return_code=1,
            elapsed_seconds=round(elapsed, 3),
            timed_out=False,
            stderr=str(exc),
            stdout="",
        )
