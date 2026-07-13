from app.core.models import StyleOptions
from app.core.style_builder import build_override_css


def test_build_override_css_light_theme() -> None:
    opts = StyleOptions(document_theme="light")
    css = build_override_css(opts)
    assert "background: #ffffff" in css
    assert opts.text_color in css
    assert opts.title_color in css


def test_build_override_css_dark_theme() -> None:
    opts = StyleOptions(document_theme="dark")
    css = build_override_css(opts)
    assert "background: #0f172a" in css


def test_build_override_css_zebra_tables() -> None:
    opts = StyleOptions(zebra_tables=True)
    css = build_override_css(opts)
    assert "nth-child(even)" in css


def test_build_override_css_no_zebra() -> None:
    opts = StyleOptions(zebra_tables=False)
    css = build_override_css(opts)
    assert "nth-child(even)" not in css


def test_build_override_css_compact_spacing() -> None:
    opts = StyleOptions(list_spacing="compact", table_density="compact")
    css = build_override_css(opts)
    assert "0.15em" in css
    assert "4px 6px" in css


def test_build_override_css_text_align() -> None:
    opts = StyleOptions(text_align="justify", heading_align="center")
    css = build_override_css(opts)
    assert "text-align: justify" in css
    assert "text-align: center" in css
