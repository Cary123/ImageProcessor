#!/usr/bin/env python3
"""Project save/load manager."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image

from image_processor.models.image_item import ImageItem
from image_processor.models.project import Project, ProjectImageData


class ProjectError(Exception):
    """Raised when project operations fail."""


class ProjectManager:
    """Saves and loads projects as directories with PNG images and JSON metadata."""

    def __init__(self) -> None:
        pass

    def save(self, project: Project, project_dir: Path) -> Path:
        project_dir = Path(project_dir).expanduser().resolve()
        project_dir.mkdir(parents=True, exist_ok=True)
        images_dir = project_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        metadata: dict[str, Any] = {
            "version": project.version,
            "current_index": project.current_index,
            "images": [],
        }

        for image_index, image_data in enumerate(project.images):
            image_meta: dict[str, Any] = {
                "source_path": str(image_data.source_path),
                "metadata": image_data.metadata,
                "history": [],
            }
            for entry_index, (description, image) in enumerate(image_data.history_entries):
                filename = f"image_{image_index}_{entry_index}.png"
                image_path = images_dir / filename
                image.save(image_path, format="PNG")
                image_meta["history"].append(
                    {
                        "description": description,
                        "file": filename,
                    }
                )
            metadata["images"].append(image_meta)

        project_file = project_dir / "project.json"
        project_file.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return project_dir

    def load(self, project_dir: Path) -> Project:
        project_dir = Path(project_dir).expanduser().resolve()
        project_file = project_dir / "project.json"
        if not project_file.is_file():
            raise ProjectError(f"Project file not found: {project_file}")

        images_dir = project_dir / "images"
        if not images_dir.is_dir():
            raise ProjectError(f"Project images directory not found: {images_dir}")

        try:
            metadata = json.loads(project_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProjectError(f"Invalid project JSON: {exc}") from exc

        version = metadata.get("version", "1.0")
        current_index = metadata.get("current_index", 0)
        images_data: list[ProjectImageData] = []

        for image_index, image_meta in enumerate(metadata.get("images", [])):
            source_path = Path(image_meta["source_path"])
            item_metadata = dict(image_meta.get("metadata", {}))
            history_entries: list[tuple[str, Image.Image]] = []

            for entry in image_meta.get("history", []):
                filename = entry["file"]
                image_path = images_dir / filename
                if not image_path.is_file():
                    raise ProjectError(f"Missing project image: {image_path}")
                try:
                    image = Image.open(image_path).convert("RGBA")
                except OSError as exc:
                    raise ProjectError(f"Failed to load project image: {image_path}") from exc
                history_entries.append((entry["description"], image))

            images_data.append(
                ProjectImageData(
                    source_path=source_path,
                    metadata=item_metadata,
                    history_entries=history_entries,
                )
            )

        return Project(
            version=version,
            current_index=current_index,
            images=images_data,
        )

    def project_from_items(
        self, items: list[ImageItem], current_index: int
    ) -> Project:
        images_data: list[ProjectImageData] = []
        for item in items:
            entries = [
                (entry.description, entry.image.copy())
                for entry in item.history._stack
            ]
            images_data.append(
                ProjectImageData(
                    source_path=item.source_path,
                    metadata=dict(item.metadata),
                    history_entries=entries,
                )
            )
        return Project(current_index=current_index, images=images_data)
