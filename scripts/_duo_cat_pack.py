from __future__ import annotations

from pathlib import Path
from typing import Any

FRAME_W = 512
FRAME_H = 256
COLS = 3
ROWS = 2
TOTAL_FRAMES = 6
ATLAS_W = FRAME_W * COLS
ATLAS_H = FRAME_H * ROWS

CLIP_ORDER = [
    "snuggle_idle",
    "mutual_groom",
    "nose_boop",
    "snuggle_curl",
    "play_pounce",
    "paw_batting",
    "chase_loop",
    "bunny_kick",
    "standing_swat",
    "standoff",
    "explosive_clash",
    "ear_cleaning",
    "face_wash_assist",
]

CLIP_CONFIG: dict[str, dict[str, Any]] = {
    "snuggle_idle": {"fps": 6, "loop": True},
    "mutual_groom": {"fps": 9, "loop": False, "return_to": "snuggle_idle"},
    "nose_boop": {"fps": 10, "loop": False, "return_to": "snuggle_idle"},
    "snuggle_curl": {"fps": 8, "loop": False, "return_to": "snuggle_idle"},
    "play_pounce": {"fps": 12, "loop": False, "return_to": "snuggle_idle"},
    "paw_batting": {"fps": 11, "loop": False, "return_to": "snuggle_idle"},
    "chase_loop": {"fps": 12, "loop": True},
    "bunny_kick": {"fps": 12, "loop": False, "return_to": "snuggle_idle"},
    "standing_swat": {"fps": 10, "loop": False, "return_to": "snuggle_idle"},
    "standoff": {"fps": 7, "loop": True},
    "explosive_clash": {"fps": 14, "loop": False, "return_to": "snuggle_idle"},
    "ear_cleaning": {"fps": 9, "loop": False, "return_to": "snuggle_idle"},
    "face_wash_assist": {"fps": 9, "loop": False, "return_to": "snuggle_idle"},
}

SOURCE_ROOT = Path("app/ui/assets_src/duo_cats")
PUBLIC_ROOT = Path("public/static/sprites/cats")
APP_STATIC_ROOT = Path("app/ui/static/sprites/cats")
ASSET_VERSION = "cat-tree-39"
SEAM_CLIPS = set(CLIP_ORDER)


def frame_rects() -> list[dict[str, int]]:
    rects: list[dict[str, int]] = []
    for frame_id in range(TOTAL_FRAMES):
        row = frame_id // COLS
        col = frame_id % COLS
        rects.append(
            {
                "id": frame_id,
                "x": col * FRAME_W,
                "y": row * FRAME_H,
                "w": FRAME_W,
                "h": FRAME_H,
            }
        )
    return rects
