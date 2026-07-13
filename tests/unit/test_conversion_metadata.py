from app.core.models import ConversionProfile, DocumentMetadata, StyleOptions, StyleProfile


def test_document_metadata_defaults() -> None:
    meta = DocumentMetadata()
    assert meta.classification == "internal"
    assert meta.language == "es"
    assert meta.title is None
    assert meta.signatures_enabled is False


def test_document_metadata_custom_values() -> None:
    meta = DocumentMetadata(
        title="Test",
        author="Author",
        classification="confidential",
        language="en",
        watermark="DRAFT",
        signatures_enabled=True,
    )
    assert meta.title == "Test"
    assert meta.classification == "confidential"
    assert meta.watermark == "DRAFT"
    assert meta.signatures_enabled is True


def test_style_options_defaults() -> None:
    opts = StyleOptions()
    assert opts.document_theme == "light"
    assert opts.zebra_tables is True
    assert opts.heading_align == "left"


def test_conversion_profile_defaults() -> None:
    profile = ConversionProfile()
    assert profile.project_name == "Reporte"
    assert profile.outputs == []
    assert profile.metadata.language == "es"
    assert profile.rules.normalize_headings is True


def test_style_profile_defaults() -> None:
    sp = StyleProfile()
    assert sp.pdf_engine is None
    assert sp.pdf_layout_mode == "web"
    assert sp.options.document_theme == "light"
