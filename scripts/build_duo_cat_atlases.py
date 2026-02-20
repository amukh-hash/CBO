from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from _duo_cat_pack import (
    APP_STATIC_ROOT,
    ASSET_VERSION,
    ATLAS_H,
    ATLAS_W,
    CLIP_CONFIG,
    CLIP_ORDER,
    COLS,
    FRAME_H,
    FRAME_W,
    PUBLIC_ROOT,
    ROWS,
    SOURCE_ROOT,
    TOTAL_FRAMES,
    frame_rects,
)

VERSION_SUFFIX = f"?v={ASSET_VERSION}"


def _versioned_image_path(path: str) -> str:
    return f"{path}{VERSION_SUFFIX}"


def _validate_frames(clip: str) -> list[Path]:
    clip_dir = SOURCE_ROOT / clip
    frame_paths = [clip_dir / f"frame_{idx}.png" for idx in range(TOTAL_FRAMES)]
    missing = [path for path in frame_paths if not path.exists()]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing frames for {clip}: {missing_text}")

    frames = [Image.open(path).convert("RGBA") for path in frame_paths]
    try:
        for idx, image in enumerate(frames):
            if image.size != (FRAME_W, FRAME_H):
                raise ValueError(f"{clip} frame_{idx}.png must be {FRAME_W}x{FRAME_H}, got {image.size}")
        # Validate frame_0 and frame_5 are the identical snuggle pose.
        if ImageChops.difference(frames[0], frames[-1]).getbbox() is not None:
            raise ValueError(f"{clip} frame_0.png and frame_5.png must be pixel-identical")
    finally:
        for image in frames:
            image.close()
    return frame_paths


def _build_atlas(frame_paths: list[Path], out_path: Path) -> None:
    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
    opened = [Image.open(path).convert("RGBA") for path in frame_paths]
    try:
        for idx, frame in enumerate(opened):
            row = idx // COLS
            col = idx % COLS
            atlas.paste(frame, (col * FRAME_W, row * FRAME_H), frame)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        atlas.save(out_path)
    finally:
        atlas.close()
        for frame in opened:
            frame.close()


def _build_debug_atlas(frame_paths: list[Path], out_path: Path) -> None:
    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
    opened = [Image.open(path).convert("RGBA") for path in frame_paths]
    try:
        draw = ImageDraw.Draw(atlas)
        for idx, frame in enumerate(opened):
            row = idx // COLS
            col = idx % COLS
            x = col * FRAME_W
            y = row * FRAME_H
            atlas.paste(frame, (x, y), frame)
            draw.rectangle((x, y, x + FRAME_W - 1, y + FRAME_H - 1), outline=(255, 0, 0, 220), width=2)
            draw.text((x + 8, y + 8), f"f{idx}", fill=(255, 255, 255, 230))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        atlas.save(out_path)
    finally:
        atlas.close()
        for frame in opened:
            frame.close()


def _runtime_meta() -> dict:
    frames = frame_rects()
    clips: dict[str, dict] = {}
    for clip in CLIP_ORDER:
        cfg = CLIP_CONFIG[clip]
        clip_entry = {
            "fps": cfg["fps"],
            "loop": cfg["loop"],
            "frames": [0, 1, 2, 3, 4, 5],
            "imagePath": _versioned_image_path(f"/static/sprites/cats/duo_cats/{clip}.png"),
        }
        if "return_to" in cfg:
            clip_entry["return_to"] = cfg["return_to"]
        clips[clip] = clip_entry

    # Backward-compatible aliases for existing dataset values.
    clips["duo_snuggle"] = {
        "fps": CLIP_CONFIG["snuggle_idle"]["fps"],
        "loop": True,
        "frames": [0, 1, 2, 3, 4, 5],
        "imagePath": _versioned_image_path("/static/sprites/cats/duo_cats/snuggle_idle.png"),
    }
    clips["duo_groom"] = {
        "fps": CLIP_CONFIG["mutual_groom"]["fps"],
        "loop": False,
        "return_to": "snuggle_idle",
        "frames": [0, 1, 2, 3, 4, 5],
        "imagePath": _versioned_image_path("/static/sprites/cats/duo_cats/mutual_groom.png"),
    }
    clips["duo_play"] = {
        "fps": CLIP_CONFIG["play_pounce"]["fps"],
        "loop": False,
        "return_to": "snuggle_idle",
        "frames": [0, 1, 2, 3, 4, 5],
        "imagePath": _versioned_image_path("/static/sprites/cats/duo_cats/play_pounce.png"),
    }

    return {
        "imagePath": _versioned_image_path("/static/sprites/cats/duo_cats/snuggle_idle.png"),
        "frameW": FRAME_W,
        "frameH": FRAME_H,
        "cols": COLS,
        "rows": ROWS,
        "default_clip": "snuggle_idle",
        "frames": frames,
        "clips": clips,
    }


def _clip_names() -> list[str]:
    return [clip for clip in CLIP_ORDER if clip in CLIP_CONFIG]


def build(debug: bool = False) -> None:
    clips = _clip_names()
    app_atlas_root = APP_STATIC_ROOT / "duo_cats"
    public_atlas_root = PUBLIC_ROOT / "duo_cats"
    for clip in clips:
        frame_paths = _validate_frames(clip)
        _build_atlas(frame_paths, app_atlas_root / f"{clip}.png")
        _build_atlas(frame_paths, public_atlas_root / f"{clip}.png")
        if debug:
            _build_debug_atlas(frame_paths, app_atlas_root / f"{clip}.debug.png")
            _build_debug_atlas(frame_paths, public_atlas_root / f"{clip}.debug.png")

    meta = _runtime_meta()
    for root in (APP_STATIC_ROOT, PUBLIC_ROOT):
        root.mkdir(parents=True, exist_ok=True)
        (root / "cats_duo_pack.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"built {len(clips)} duo-cat atlases to {app_atlas_root} and {public_atlas_root}")
    print(f"wrote runtime metadata to {APP_STATIC_ROOT / 'cats_duo_pack.json'} and {PUBLIC_ROOT / 'cats_duo_pack.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build 3x2 duo-cat atlases and regenerate runtime metadata.")
    parser.add_argument("--debug", action="store_true", help="also export debug atlases with grid lines")
    args = parser.parse_args()
    build(debug=args.debug)
