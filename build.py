#!/usr/bin/env python3
"""Build script for packaging ImageProcessor with PyInstaller."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"


def clean() -> None:
    """Remove previous build artifacts."""
    for directory in (DIST_DIR, BUILD_DIR):
        if directory.exists():
            shutil.rmtree(directory)
            print(f"Removed {directory}")


def build() -> int:
    """Run PyInstaller to create the app bundle."""
    clean()
    spec_file = PROJECT_ROOT / "ImageProcessor.spec"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(spec_file),
        "--noconfirm",
    ]
    print("Running:", " ".join(command))
    result = subprocess.run(command, cwd=PROJECT_ROOT)
    return result.returncode


def package() -> Path | None:
    """Zip the generated app bundle for distribution."""
    app_path = DIST_DIR / "ImageProcessor.app"
    if not app_path.exists():
        print(f"App not found at {app_path}")
        return None

    zip_path = DIST_DIR / "ImageProcessor-macOS"
    shutil.make_archive(str(zip_path), "zip", root_dir=DIST_DIR, base_dir="ImageProcessor.app")
    final_zip = zip_path.with_suffix(".zip")
    print(f"Created {final_zip}")
    return final_zip


def main() -> int:
    return_code = build()
    if return_code != 0:
        return return_code
    package()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
