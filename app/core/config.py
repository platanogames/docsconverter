from __future__ import annotations

from pathlib import Path

import yaml

from app.core.models import ConversionProfile


def load_profile(profile_path: Path) -> ConversionProfile:
    with profile_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    profile = ConversionProfile.model_validate(data)
    return _resolve_profile_assets(profile, profile_path.parent)


def save_profile(profile: ConversionProfile, profile_path: Path) -> None:
    payload = profile.model_dump(mode="json")
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    with profile_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def _resolve_profile_assets(profile: ConversionProfile, base_dir: Path) -> ConversionProfile:
    if profile.style_profile.template_html and not profile.style_profile.template_html.is_absolute():
        profile.style_profile.template_html = (base_dir / profile.style_profile.template_html).resolve()
    if profile.style_profile.template_pdf and not profile.style_profile.template_pdf.is_absolute():
        profile.style_profile.template_pdf = (base_dir / profile.style_profile.template_pdf).resolve()
    if profile.style_profile.css and not profile.style_profile.css.is_absolute():
        profile.style_profile.css = (base_dir / profile.style_profile.css).resolve()
    if profile.style_profile.latex_header and not profile.style_profile.latex_header.is_absolute():
        profile.style_profile.latex_header = (base_dir / profile.style_profile.latex_header).resolve()
    return profile
