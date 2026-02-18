from __future__ import annotations

from pathlib import Path

import yaml

from app.core.sanitizer import SanitizationConfig


def load_sanitization_config(path: Path) -> SanitizationConfig:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return SanitizationConfig.model_validate(data)
