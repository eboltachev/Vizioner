from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelInfo:
    id: str
    type: str
    description: str


def load_models(models_root: Path) -> list[ModelInfo]:
    models: list[ModelInfo] = []
    if not models_root.exists():
        return models
    for model_type_dir in sorted(p for p in models_root.iterdir() if p.is_dir()):
        for model_dir in sorted(p for p in model_type_dir.iterdir() if p.is_dir()):
            model_id = model_dir.name
            readme_path = model_dir / "README.md"
            if readme_path.exists():
                description = readme_path.read_text(encoding="utf-8").strip() or f"{model_type_dir.name}/{model_id}"
            else:
                description = f"{model_type_dir.name}/{model_id}"
            models.append(
                ModelInfo(
                    id=model_id,
                    type=model_type_dir.name,
                    description=description,
                )
            )
    return models
