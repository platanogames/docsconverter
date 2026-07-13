from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_PROFILE = PROJECT_ROOT / "configs/profiles/fixtures-complex.yaml"
DEFAULT_INPUTS = [
    PROJECT_ROOT / "fixtures/complex_markdown/01-corporate-report.md",
    PROJECT_ROOT / "fixtures/complex_markdown/02-technical-rfc.md",
    PROJECT_ROOT / "fixtures/complex_markdown/03-knowledge-base.md",
    PROJECT_ROOT / "fixtures/complex_markdown/04-release-notes-heavy.md",
]


def run_case(input_path: Path, profile_path: Path) -> int:
    cmd = [
        sys.executable,
        "-m",
        "app.main",
        "convert",
        "--input",
        str(input_path),
        "--profile",
        str(profile_path),
    ]
    print(f"-> Convirtiendo: {input_path}")
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta conversion de fixtures complejos")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE, help="Perfil YAML a usar")
    args = parser.parse_args()

    profile = (PROJECT_ROOT / args.profile).resolve() if not args.profile.is_absolute() else args.profile
    if not profile.exists():
        print(f"Perfil no encontrado: {profile}")
        return 2

    print("== Ejecutando conversion de fixtures complejos ==")
    for input_path in DEFAULT_INPUTS:
        if not input_path.exists():
            print(f"Input no encontrado: {input_path}")
            return 2
        rc = run_case(input_path, profile)
        if rc != 0:
            print(f"Fallo en conversion de: {input_path}")
            return rc
    print("Ejecucion completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
