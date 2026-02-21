from __future__ import annotations

from pathlib import Path
from typing import Any

FRAME_W = 512
FRAME_H = 256
COLS = 3
ROWS = 2
CELLS_PER_PAGE = COLS * ROWS
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
    "snuggle_idle": {
        "fps": 7,
        "loop": True,
        "frame_count": 24,
        "tags": ["idle", "affection"],
        "seam": True,
    },
    "mutual_groom": {
        "fps": 10,
        "loop": False,
        "return_to": "snuggle_idle",
        "frame_count": 12,
        "tags": ["affection", "groom", "interaction"],
        "cooldown_ms": 700,
        "seam": True,
    },
    "nose_boop": {
        "fps": 10,
        "loop": False,
        "return_to": "snuggle_idle",
        "frame_count": 10,
        "tags": ["affection", "boop", "interaction"],
        "cooldown_ms": 500,
        "seam": True,
    },
    "snuggle_curl": {
        "fps": 8,
        "loop": False,
        "return_to": "snuggle_idle",
        "frame_count": 10,
        "tags": ["affection", "idle", "curl"],
        "hold_last_ms": 400,
        "seam": True,
    },
    "play_pounce": {
        "fps": 12,
        "loop": False,
        "return_to": "snuggle_idle",
        "frame_count": 12,
        "tags": ["play", "pounce", "interaction"],
        "cooldown_ms": 600,
        "seam": True,
    },
    "paw_batting": {
        "fps": 11,
        "loop": False,
        "return_to": "snuggle_idle",
        "frame_count": 12,
        "tags": ["play", "paw", "interaction"],
        "cooldown_ms": 600,
        "seam": True,
    },
    "chase_loop": {
        "fps": 12,
        "loop": False,
        "return_to": "snuggle_idle",
        "frame_count": 12,
        "tags": ["play", "chase", "motion"],
        "seam": False,
    },
    "bunny_kick": {
        "fps": 12,
        "loop": False,
        "return_to": "snuggle_idle",
        "frame_count": 14,
        "tags": ["play", "kick", "interaction"],
        "cooldown_ms": 700,
        "seam": True,
    },
    "standing_swat": {
        "fps": 10,
        "loop": False,
        "return_to": "snuggle_idle",
        "frame_count": 12,
        "tags": ["play", "swat", "interaction"],
        "cooldown_ms": 600,
        "seam": True,
    },
    "standoff": {
        "fps": 8,
        "loop": False,
        "return_to": "snuggle_idle",
        "frame_count": 10,
        "tags": ["mood", "standoff"],
        "cooldown_ms": 900,
        "seam": True,
    },
    "explosive_clash": {
        "fps": 13,
        "loop": False,
        "return_to": "snuggle_idle",
        "frame_count": 10,
        "tags": ["mood", "clash", "interaction"],
        "cooldown_ms": 1000,
        "seam": True,
    },
    "ear_cleaning": {
        "fps": 9,
        "loop": False,
        "return_to": "snuggle_idle",
        "frame_count": 10,
        "tags": ["affection", "groom", "care"],
        "cooldown_ms": 600,
        "seam": True,
    },
    "face_wash_assist": {
        "fps": 9,
        "loop": False,
        "return_to": "snuggle_idle",
        "frame_count": 10,
        "tags": ["affection", "groom", "care"],
        "cooldown_ms": 600,
        "seam": True,
    },
}

LIBRARY: dict[str, Any] = {
    "foundation": "snuggle_idle",
    "groups": {
        "affection": ["nose_boop", "mutual_groom", "ear_cleaning", "face_wash_assist", "snuggle_curl"],
        "play": ["paw_batting", "play_pounce", "bunny_kick", "standing_swat", "chase_loop"],
        "mood": ["standoff", "explosive_clash"],
    },
    "playlists": {
        "showcase_all": {
            "mode": "sequence",
            "idle_clip": "snuggle_idle",
            "idle_hold_ms": 4000,
            "between_hold_ms": 700,
            "clips": [
                "nose_boop",
                "mutual_groom",
                "paw_batting",
                "play_pounce",
                "bunny_kick",
                "standing_swat",
                "ear_cleaning",
                "face_wash_assist",
                "snuggle_curl",
                "chase_loop",
                "standoff",
                "explosive_clash",
            ],
        },
        "ambient_random": {
            "mode": "weighted_random",
            "idle_clip": "snuggle_idle",
            "idle_hold_ms_range": [5000, 12000],
            "between_hold_ms_range": [300, 900],
            "pool": [
                ["nose_boop", 2],
                ["mutual_groom", 3],
                ["paw_batting", 2],
                ["play_pounce", 2],
                ["ear_cleaning", 2],
                ["face_wash_assist", 2],
                ["snuggle_curl", 3],
                ["bunny_kick", 1],
                ["standing_swat", 1],
            ],
        },
    },
}

SOURCE_ROOT = Path("app/ui/assets_src/duo_cats")
PUBLIC_ROOT = Path("public/static/sprites/cats")
APP_STATIC_ROOT = Path("app/ui/static/sprites/cats")
ASSET_VERSION = "cat-tree-41"
SEAM_CLIPS = {clip for clip, cfg in CLIP_CONFIG.items() if bool(cfg.get("seam", True))}


def clip_frame_count(clip: str) -> int:
    cfg = CLIP_CONFIG.get(clip, {})
    count = cfg.get("frame_count", CELLS_PER_PAGE)
    if not isinstance(count, int) or count <= 0:
        raise ValueError(f"Invalid frame_count for clip '{clip}': {count}")
    return count


def frame_rects() -> list[dict[str, int]]:
    rects: list[dict[str, int]] = []
    for frame_id in range(CELLS_PER_PAGE):
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
