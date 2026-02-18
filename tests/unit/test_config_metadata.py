from pathlib import Path

from app.core.config import load_profile, save_profile
from app.core.models import ConversionProfile, DocumentMetadata, OutputTarget


def test_save_and_load_profile_persists_metadata() -> None:
    profile_path = Path("build/test-artifacts/profile-metadata.yaml")
    profile_path.parent.mkdir(parents=True, exist_ok=True)

    profile = ConversionProfile(
        project_name="Metadata Test",
        outputs=[OutputTarget(format="html", output_path=Path("build/out.html"))],
        metadata=DocumentMetadata(
            title="Documento Arquitectura",
            subtitle="Sprint 4",
            author="Equipo Plataforma",
            reviewer="Arquitecto Principal",
            version="2.0",
            classification="confidential",
            language="es",
            date="2026-02-17",
        ),
    )
    save_profile(profile, profile_path)

    loaded = load_profile(profile_path)
    assert loaded.metadata.title == "Documento Arquitectura"
    assert loaded.metadata.subtitle == "Sprint 4"
    assert loaded.metadata.author == "Equipo Plataforma"
    assert loaded.metadata.reviewer == "Arquitecto Principal"
    assert loaded.metadata.version == "2.0"
    assert loaded.metadata.classification == "confidential"
    assert loaded.metadata.language == "es"
    assert loaded.metadata.date == "2026-02-17"
