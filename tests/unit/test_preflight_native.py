from unittest.mock import patch

from app.core.preflight import _detect_pdf_engine


def test_detect_pdf_engine_web_mode_wkhtmltopdf() -> None:
    with patch("app.core.preflight.shutil.which", side_effect=lambda e: "/usr/bin/wkhtmltopdf" if e == "wkhtmltopdf" else None):
        assert _detect_pdf_engine("web") == "wkhtmltopdf"


def test_detect_pdf_engine_native_mode_xelatex() -> None:
    with patch("app.core.preflight.shutil.which", side_effect=lambda e: "/usr/bin/xelatex" if e == "xelatex" else None):
        assert _detect_pdf_engine("native") == "xelatex"


def test_detect_pdf_engine_native_mode_pdflatex_fallback() -> None:
    def mock_which(engine: str) -> str | None:
        return "/usr/bin/pdflatex" if engine == "pdflatex" else None
    with patch("app.core.preflight.shutil.which", side_effect=mock_which):
        assert _detect_pdf_engine("native") == "pdflatex"


def test_detect_pdf_engine_web_mode_falls_back_to_native() -> None:
    def mock_which(engine: str) -> str | None:
        return "/usr/bin/xelatex" if engine == "xelatex" else None
    with patch("app.core.preflight.shutil.which", side_effect=mock_which):
        assert _detect_pdf_engine("web") == "xelatex"


def test_detect_pdf_engine_none_when_nothing_available() -> None:
    with patch("app.core.preflight.shutil.which", return_value=None):
        assert _detect_pdf_engine("web") is None
        assert _detect_pdf_engine("native") is None
