from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops
import hashlib
from urllib.parse import urlparse

from _duo_cat_pack import (
    APP_STATIC_ROOT,
    ATLAS_H,
    ATLAS_W,
    CLIP_ORDER,
    FRAME_H,
    FRAME_W,
    PUBLIC_ROOT,
    SEAM_CLIPS,
    SOURCE_ROOT,
    TOTAL_FRAMES,
)

MIN_ALPHA_PIXELS = 1500


def _validate_meta(meta_path: Path) -> dict:
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing metadata: {meta_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    required = ("frameW", "frameH", "cols", "rows", "clips", "frames")
    missing = [name for name in required if name not in meta]
    if missing:
        raise ValueError(f"Metadata missing keys: {missing}")
    if meta["frameW"] != FRAME_W or meta["frameH"] != FRAME_H:
        raise ValueError(f"Expected frame size {FRAME_W}x{FRAME_H}, got {meta['frameW']}x{meta['frameH']}")
    return meta


def _validate_sources(clip: str) -> None:
    frame_paths = [SOURCE_ROOT / clip / f"frame_{idx}.png" for idx in range(TOTAL_FRAMES)]
    missing = [str(path) for path in frame_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing source frame(s) for {clip}: {', '.join(missing)}")

    frames = [Image.open(path).convert("RGBA") for path in frame_paths]
    try:
        for idx, frame in enumerate(frames):
            if frame.size != (FRAME_W, FRAME_H):
                raise ValueError(f"{clip} frame_{idx}.png has invalid size {frame.size}")
        if clip in SEAM_CLIPS and ImageChops.difference(frames[0], frames[5]).getbbox() is not None:
            raise ValueError(f"{clip}: frame_0 and frame_5 are not pixel-identical")
    finally:
        for frame in frames:
            frame.close()


def _path_from_image_url(root: Path, image_url: str) -> Path:
    parsed = urlparse(image_url)
    path = parsed.path
    if not path.startswith("/static/sprites/cats/"):
        raise ValueError(f"Unsupported imagePath '{image_url}' (expected /static/sprites/cats/...)")
    rel = path.removeprefix("/static/sprites/cats/")
    return root / rel


def _validate_outputs(root: Path, clip: str, atlas: Path) -> None:
    gif = root / "duo_cats_gifs" / f"{clip}.gif"
    if not atlas.exists():
        raise FileNotFoundError(f"Missing atlas: {atlas}")
    if not gif.exists():
        raise FileNotFoundError(f"Missing GIF: {gif}")
    with Image.open(atlas) as atlas_img:
        if atlas_img.size != (ATLAS_W, ATLAS_H):
            raise ValueError(f"{atlas} must be {ATLAS_W}x{ATLAS_H}, got {atlas_img.size}")
        # Catch accidental packer regressions where every atlas cell is duplicated.
        cell_hashes: list[str] = []
        for idx in range(TOTAL_FRAMES):
            col = idx % 3
            row = idx // 3
            x0 = col * FRAME_W
            y0 = row * FRAME_H
            cell_img = atlas_img.crop((x0, y0, x0 + FRAME_W, y0 + FRAME_H))
            alpha_band = cell_img.getchannel("A")
            alpha_hist = alpha_band.histogram()
            alpha_count = sum(alpha_hist[9:])
            if alpha_count < MIN_ALPHA_PIXELS:
                raise ValueError(
                    f"{atlas} cell f{idx} is mostly empty (alpha>8 pixels={alpha_count}, min={MIN_ALPHA_PIXELS})"
                )
            cell_hashes.append(hashlib.sha256(cell_img.tobytes()).hexdigest())
        if len(set(cell_hashes)) == 1:
            raise ValueError(f"{atlas} appears static: all six cells are pixel-identical")
        if clip == "snuggle_idle" and len(set(cell_hashes)) < 2:
            raise ValueError(f"{atlas} snuggle_idle must contain at least 2 distinct frames")
        if clip in SEAM_CLIPS and cell_hashes[0] != cell_hashes[5]:
            raise ValueError(f"{atlas} seam check failed: frame 0 and frame 5 differ")


def validate() -> None:
    app_meta = _validate_meta(APP_STATIC_ROOT / "cats_duo_pack.json")
    public_meta = _validate_meta(PUBLIC_ROOT / "cats_duo_pack.json")

    for clip in CLIP_ORDER:
        if clip not in app_meta["clips"]:
            raise ValueError(f"Clip '{clip}' missing from app runtime metadata")
        if clip not in public_meta["clips"]:
            raise ValueError(f"Clip '{clip}' missing from public runtime metadata")
        _validate_sources(clip)
        app_atlas = _path_from_image_url(APP_STATIC_ROOT, app_meta["clips"][clip]["imagePath"])
        public_atlas = _path_from_image_url(PUBLIC_ROOT, public_meta["clips"][clip]["imagePath"])
        _validate_outputs(APP_STATIC_ROOT, clip, app_atlas)
        _validate_outputs(PUBLIC_ROOT, clip, public_atlas)
        clip_frames = app_meta["clips"][clip].get("frames", [])
        if not clip_frames or clip_frames[0] != 0:
            raise ValueError(f"Clip '{clip}' must start at frame id 0")
        if clip_frames[-1] != 5:
            raise ValueError(f"Clip '{clip}' must end at frame id 5")

    print("duo-cat pack validation passed")


if __name__ == "__main__":
    validate()
