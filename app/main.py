from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as `python app/main.py` (Rider) or `python -m app.main`
if __name__ == "__main__":
    _project_root = str(Path(__file__).resolve().parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

from app.core.batch import collect_markdown_files, retarget_outputs_for_input
from app.core.config import load_profile
from app.core.models import ConversionJob
from app.core.paths import get_default_pandoc_path, get_user_data_dir
from app.core.pipeline import run_conversion_job
from app.core.preflight import preflight_or_raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DocsConverter")
    parser.add_argument("--pandoc", type=Path, default=None, help="Ruta a pandoc.exe")

    subparsers = parser.add_subparsers(dest="command", required=True)

    cmd_convert = subparsers.add_parser("convert", help="Ejecuta conversion de documento")
    cmd_convert.add_argument("--input", type=Path, required=True, help="Archivo markdown de entrada")
    cmd_convert.add_argument("--profile", type=Path, required=True, help="Perfil YAML de conversion")
    cmd_convert.add_argument("--history", type=Path, default=None, help="Ruta de historial")

    cmd_convert_dir = subparsers.add_parser("convert-dir", help="Ejecuta conversion por lote de carpeta")
    cmd_convert_dir.add_argument("--input-dir", type=Path, required=True, help="Carpeta con markdowns")
    cmd_convert_dir.add_argument("--profile", type=Path, required=True, help="Perfil YAML de conversion")
    cmd_convert_dir.add_argument("--history", type=Path, default=None, help="Ruta de historial")
    cmd_convert_dir.add_argument("--pattern", type=str, default="*.md", help="Patron glob de entrada")
    cmd_convert_dir.add_argument("--no-recursive", action="store_true", help="No incluir subcarpetas")

    subparsers.add_parser("ui", help="Abre la interfaz de escritorio")
    return parser


def _resolve_args(args: argparse.Namespace) -> None:
    """Fill in default values that depend on runtime path resolution."""
    if args.pandoc is None:
        args.pandoc = get_default_pandoc_path()
    if hasattr(args, "history") and args.history is None:
        args.history = get_user_data_dir() / "logs" / "history.jsonl"


def run_convert(args: argparse.Namespace) -> int:
    _resolve_args(args)
    profile = load_profile(args.profile)
    had_configured_pdf_engine = bool(profile.style_profile.pdf_engine)
    job = ConversionJob(
        input_path=args.input,
        profile_path=args.profile,
        outputs=profile.outputs,
        style_profile=profile.style_profile,
        metadata=profile.metadata,
        rules=profile.rules,
    )
    if not job.metadata.title:
        job.metadata.title = profile.project_name
    resolved_pandoc, detected_engine = preflight_or_raise(job, args.pandoc)
    if detected_engine and not had_configured_pdf_engine:
        print(f"[preflight] motor PDF detectado automaticamente: {detected_engine}")
    results = run_conversion_job(job, pandoc_path=resolved_pandoc, history_path=args.history)
    has_error = False
    for result in results:
        print(
            f"[{result.output.format}] rc={result.return_code} "
            f"elapsed={result.elapsed_seconds:.2f}s timeout={result.timed_out} "
            f"output={result.output.output_path}"
        )
        if result.stderr.strip():
            print(result.stderr.strip())
        has_error = has_error or (result.return_code != 0)
    return 1 if has_error else 0


def run_ui(args: argparse.Namespace) -> int:
    _resolve_args(args)
    try:
        from app.ui.window import run_ui as _run_ui
    except ImportError as exc:
        print("PySide6 no instalado. Ejecuta: pip install .[ui]")
        print(f"Detalle: {exc}")
        return 2
    _run_ui(pandoc_path=args.pandoc)
    return 0


def run_convert_dir(args: argparse.Namespace) -> int:
    _resolve_args(args)
    profile = load_profile(args.profile)
    recursive = not args.no_recursive
    input_dir = args.input_dir.resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Carpeta de entrada no valida: {input_dir}")
        return 2

    files = collect_markdown_files(input_dir, pattern=args.pattern, recursive=recursive)
    if not files:
        print(f"No se encontraron archivos para patron '{args.pattern}' en {input_dir}")
        return 2

    total_errors = 0
    print(f"[batch] archivos detectados: {len(files)}")
    for input_file in files:
        job = ConversionJob(
            input_path=input_file,
            profile_path=args.profile,
            outputs=retarget_outputs_for_input(profile.outputs, input_file),
            style_profile=profile.style_profile.model_copy(deep=True),
            metadata=profile.metadata.model_copy(deep=True),
            rules=profile.rules.model_copy(deep=True),
            build_dir=get_user_data_dir() / "build" / "batch" / input_file.stem,
        )
        if not job.metadata.title:
            job.metadata.title = f"{profile.project_name} - {input_file.stem}"
        print(f"[batch] convirtiendo: {input_file}")
        try:
            resolved_pandoc, _ = preflight_or_raise(job, args.pandoc)
            results = run_conversion_job(job, pandoc_path=resolved_pandoc, history_path=args.history)
            for result in results:
                print(
                    f"  [{result.output.format}] rc={result.return_code} "
                    f"elapsed={result.elapsed_seconds:.2f}s timeout={result.timed_out} "
                    f"-> {result.output.output_path}"
                )
                if result.return_code != 0:
                    total_errors += 1
        except Exception as exc:  # pragma: no cover
            total_errors += 1
            print(f"  [error] {exc}")

    return 1 if total_errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "convert":
        return run_convert(args)
    if args.command == "convert-dir":
        return run_convert_dir(args)
    if args.command == "ui":
        return run_ui(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
