from __future__ import annotations

from pathlib import Path

from app.core.models import OutputTarget


def collect_markdown_files(
    input_dir: Path, pattern: str = "*.md", recursive: bool = True
) -> list[Path]:
    if recursive:
        files = sorted(input_dir.rglob(pattern))
    else:
        files = sorted(input_dir.glob(pattern))
    return [f for f in files if f.is_file()]


def retarget_outputs_for_input(
    outputs: list[OutputTarget], input_file: Path
) -> list[OutputTarget]:
    result: list[OutputTarget] = []
    stem = input_file.stem
    for out in outputs:
        new_path = out.output_path.parent / f"{stem}{out.output_path.suffix}"
        result.append(OutputTarget(format=out.format, output_path=new_path))
    return result
