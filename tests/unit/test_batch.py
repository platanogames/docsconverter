from pathlib import Path

from app.core.batch import collect_markdown_files, retarget_outputs_for_input
from app.core.models import OutputTarget


def test_collect_markdown_files(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# A")
    (tmp_path / "b.txt").write_text("not md")
    (tmp_path / "c.md").write_text("# C")
    files = collect_markdown_files(tmp_path, pattern="*.md", recursive=False)
    assert len(files) == 2
    assert all(f.suffix == ".md" for f in files)


def test_collect_markdown_files_recursive(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "root.md").write_text("# Root")
    (sub / "nested.md").write_text("# Nested")
    files = collect_markdown_files(tmp_path, pattern="*.md", recursive=True)
    assert len(files) == 2


def test_collect_markdown_files_non_recursive(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "root.md").write_text("# Root")
    (sub / "nested.md").write_text("# Nested")
    files = collect_markdown_files(tmp_path, pattern="*.md", recursive=False)
    assert len(files) == 1


def test_retarget_outputs_for_input() -> None:
    outputs = [
        OutputTarget(format="html", output_path=Path("build/output/report.html")),
        OutputTarget(format="pdf", output_path=Path("build/output/report.pdf")),
    ]
    result = retarget_outputs_for_input(outputs, Path("docs/my-doc.md"))
    assert result[0].output_path == Path("build/output/my-doc.html")
    assert result[1].output_path == Path("build/output/my-doc.pdf")
    assert result[0].format == "html"
    assert result[1].format == "pdf"
