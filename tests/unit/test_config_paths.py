from pathlib import Path

from app.core.config import load_profile


def test_load_profile_resolves_style_paths_relative_to_profile() -> None:
    profile = load_profile(Path("configs/profiles/default.yaml"))
    assert profile.style_profile.template_html is not None
    assert profile.style_profile.css is not None
    assert profile.style_profile.template_html.exists()
    assert profile.style_profile.css.exists()

