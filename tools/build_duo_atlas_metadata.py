from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image

ATLAS_PATH = Path("app/ui/static/sprites/cats/cats_duo_atlas.png")
OUTPUT_PATH = Path("app/ui/static/sprites/cats/cats_duo_atlas.json")

ATLAS_WIDTH = 1536
ATLAS_HEIGHT = 512
COLS = 3
ROWS = 2
FRAME_W = 512
FRAME_H = 256
TOTAL_FRAMES = 6


def build_metadata(atlas_path: Path) -> dict[str, Any]:
    with Image.open(atlas_path) as image:
        width, height = image.size

    if (width, height) != (ATLAS_WIDTH, ATLAS_HEIGHT):
        raise ValueError(f"atlas must be {ATLAS_WIDTH}x{ATLAS_HEIGHT}, got {width}x{height}")

    frames: list[dict[str, int]] = []
    for frame_id in range(TOTAL_FRAMES):
        row = frame_id // COLS
        col = frame_id % COLS
        frames.append(
            {
                "id": frame_id,
                "x": col * FRAME_W,
                "y": row * FRAME_H,
                "w": FRAME_W,
                "h": FRAME_H,
            }
        )

    clips = {
        "duo_groom": {"frames": [0, 1], "fps": 10, "loop": True},
        "duo_play": {"frames": [2, 3], "fps": 12, "loop": True},
        "duo_snuggle": {"frames": [4, 5], "fps": 6, "loop": True},
    }

    return {
        "imagePath": "/static/sprites/cats/cats_duo_atlas.png",
        "frameW": FRAME_W,
        "frameH": FRAME_H,
        "cols": COLS,
        "rows": ROWS,
        "frames": frames,
        "clips": clips,
    }


def write_metadata(atlas_path: Path = ATLAS_PATH, output_path: Path = OUTPUT_PATH) -> Path:
    metadata = build_metadata(atlas_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    written = write_metadata()
    print(f"wrote {written}")
