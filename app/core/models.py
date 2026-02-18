from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    author: str | None = None
    reviewer: str | None = None
    version: str | None = None
    classification: str = "internal"
    language: str = "es"
    date: str | None = None
    header_left: str | None = None
    header_center: str | None = None
    header_right: str | None = None
    footer_left: str | None = None
    footer_center: str | None = None
    footer_right: str | None = None
    watermark: str | None = None
    approver: str | None = None
    approval_date: str | None = None
    signatures_enabled: bool = False


class StyleOptions(BaseModel):
    document_theme: str = "light"
    heading_align: str = "left"
    text_align: str = "left"
    list_spacing: str = "normal"
    table_density: str = "normal"
    zebra_tables: bool = True
    title_color: str = "#0f172a"
    text_color: str = "#1f2937"
    table_header_bg: str = "#f8fafc"
    table_border_color: str = "#d1d5db"
    accent_color: str = "#0f766e"


class StyleProfile(BaseModel):
    pdf_engine: str | None = None
    pdf_layout_mode: str = "web"
    template_html: Path | None = None
    template_pdf: Path | None = None
    css: Path | None = None
    latex_header: Path | None = None
    options: StyleOptions = Field(default_factory=StyleOptions)


class OutputTarget(BaseModel):
    format: str
    output_path: Path


class RuleSet(BaseModel):
    normalize_headings: bool = True
    fix_code_fences: bool = True
    sanitize_links: bool = False


class ConversionProfile(BaseModel):
    project_name: str = "Reporte"
    outputs: list[OutputTarget] = Field(default_factory=list)
    style_profile: StyleProfile = Field(default_factory=StyleProfile)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    rules: RuleSet = Field(default_factory=RuleSet)


class ConversionJob(BaseModel):
    input_path: Path
    profile_path: Path | None = None
    outputs: list[OutputTarget] = Field(default_factory=list)
    style_profile: StyleProfile = Field(default_factory=StyleProfile)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    rules: RuleSet = Field(default_factory=RuleSet)
    build_dir: Path | None = None


class ConversionResult(BaseModel):
    output: OutputTarget
    return_code: int
    elapsed_seconds: float
    timed_out: bool
    stderr: str = ""
    stdout: str = ""
