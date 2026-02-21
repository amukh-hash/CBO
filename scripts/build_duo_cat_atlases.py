from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from _duo_cat_pack import (
    APP_STATIC_ROOT,
    ASSET_VERSION,
    ATLAS_H,
    ATLAS_W,
    CELLS_PER_PAGE,
    CLIP_CONFIG,
    CLIP_ORDER,
    COLS,
    FRAME_H,
    FRAME_W,
    LIBRARY,
    PUBLIC_ROOT,
    ROWS,
    SEAM_CLIPS,
    SOURCE_ROOT,
    clip_frame_count,
    frame_rects,
)

VERSION_SUFFIX = f"?v={ASSET_VERSION}"
FRAME_FILE_RE = re.compile(r"^frame_(\d+)\.png$")


def _versioned_image_path(path: str) -> str:
    return f"{path}{VERSION_SUFFIX}"


def _frame_idx(path: Path) -> int:
    match = FRAME_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Invalid source frame name '{path.name}' (expected frame_000.png style)")
    return int(match.group(1))


def _clip_frame_paths(clip: str) -> list[Path]:
    clip_dir = SOURCE_ROOT / clip
    if not clip_dir.exists():
        raise FileNotFoundError(f"Missing source clip directory: {clip_dir}")

    frame_paths = [path for path in clip_dir.glob("frame_*.png") if FRAME_FILE_RE.match(path.name)]
    if not frame_paths:
        raise FileNotFoundError(f"No source frames found for clip '{clip}' in {clip_dir}")

    frame_paths.sort(key=_frame_idx)
    expected = list(range(len(frame_paths)))
    actual = [_frame_idx(path) for path in frame_paths]
    if actual != expected:
        raise ValueError(f"{clip} frames must be contiguous from 0..N-1, got indices={actual}")

    configured_count = clip_frame_count(clip)
    if len(frame_paths) != configured_count:
        raise ValueError(
            f"{clip} expected {configured_count} source frames from config, found {len(frame_paths)} in {clip_dir}"
        )

    frames = [Image.open(path).convert("RGBA") for path in frame_paths]
    try:
        for idx, image in enumerate(frames):
            if image.size != (FRAME_W, FRAME_H):
                raise ValueError(f"{clip} frame_{idx:03d}.png must be {FRAME_W}x{FRAME_H}, got {image.size}")
        if clip in SEAM_CLIPS and ImageChops.difference(frames[0], frames[-1]).getbbox() is not None:
            raise ValueError(f"{clip} seam invalid: first and last source frame must be pixel-identical")
    finally:
        for image in frames:
            image.close()

    return frame_paths


def _clear_old_outputs(root: Path, clip: str) -> None:
    atlas_root = root / "duo_cats"
    for pattern in (f"{clip}.png", f"{clip}.debug.png", f"{clip}_p*.png", f"{clip}_p*.debug.png"):
        for path in atlas_root.glob(pattern):
            path.unlink()


def _page_frames(frame_paths: list[Path], page_idx: int) -> list[Path]:
    start = page_idx * CELLS_PER_PAGE
    end = min(start + CELLS_PER_PAGE, len(frame_paths))
    return frame_paths[start:end]


def _build_page(paths: list[Path], out_path: Path, *, frame_offset: int, debug: bool) -> None:
    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
    opened = [Image.open(path).convert("RGBA") for path in paths]
    try:
        draw = ImageDraw.Draw(atlas) if debug else None
        for local_idx, frame in enumerate(opened):
            row = local_idx // COLS
            col = local_idx % COLS
            x = col * FRAME_W
            y = row * FRAME_H
            atlas.paste(frame, (x, y), frame)
            if draw is not None:
                global_idx = frame_offset + local_idx
                draw.rectangle((x, y, x + FRAME_W - 1, y + FRAME_H - 1), outline=(255, 0, 0, 220), width=2)
                draw.text((x + 8, y + 8), f"f{global_idx}", fill=(255, 255, 255, 230))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        atlas.save(out_path)
    finally:
        atlas.close()
        for frame in opened:
            frame.close()


def _build_clip_pages(frame_paths: list[Path], root: Path, clip: str, *, debug: bool) -> int:
    page_count = (len(frame_paths) + CELLS_PER_PAGE - 1) // CELLS_PER_PAGE
    atlas_root = root / "duo_cats"
    for page_idx in range(page_count):
        page_paths = _page_frames(frame_paths, page_idx)
        if not page_paths:
            continue
        out_path = atlas_root / f"{clip}_p{page_idx}.png"
        _build_page(page_paths, out_path, frame_offset=page_idx * CELLS_PER_PAGE, debug=False)
        if debug:
            debug_out_path = atlas_root / f"{clip}_p{page_idx}.debug.png"
            _build_page(page_paths, debug_out_path, frame_offset=page_idx * CELLS_PER_PAGE, debug=True)
    return page_count


def _timeline(frame_count: int) -> list[list[int]]:
    values: list[list[int]] = []
    for frame_idx in range(frame_count):
        page_idx = frame_idx // CELLS_PER_PAGE
        cell_idx = frame_idx % CELLS_PER_PAGE
        values.append([page_idx, cell_idx])
    return values


def _clip_entry(clip: str, *, frame_count: int, page_count: int) -> dict:
    cfg = CLIP_CONFIG[clip]
    pages = [
        {
            "imagePath": _versioned_image_path(f"/static/sprites/cats/duo_cats/{clip}_p{page_idx}.png"),
        }
        for page_idx in range(page_count)
    ]
    entry: dict[str, object] = {
        "fps": cfg["fps"],
        "loop": cfg["loop"],
        "frame_count": frame_count,
        "imagePath": pages[0]["imagePath"],
        "pages": pages,
        "timeline": _timeline(frame_count),
        "tags": list(cfg.get("tags", [])),
    }
    if "return_to" in cfg:
        entry["return_to"] = cfg["return_to"]
    if "cooldown_ms" in cfg:
        entry["cooldown_ms"] = cfg["cooldown_ms"]
    if "hold_last_ms" in cfg:
        entry["hold_last_ms"] = cfg["hold_last_ms"]
    return entry


def _runtime_meta(frame_counts: dict[str, int], page_counts: dict[str, int]) -> dict:
    clips: dict[str, dict] = {}
    for clip in CLIP_ORDER:
        clips[clip] = _clip_entry(clip, frame_count=frame_counts[clip], page_count=page_counts[clip])

    alias_map = {
        "duo_snuggle": "snuggle_idle",
        "duo_groom": "mutual_groom",
        "duo_play": "play_pounce",
    }
    for alias, source_clip in alias_map.items():
        clips[alias] = copy.deepcopy(clips[source_clip])

    return {
        "version": 2,
        "imagePath": _versioned_image_path("/static/sprites/cats/duo_cats/snuggle_idle_p0.png"),
        "frameW": FRAME_W,
        "frameH": FRAME_H,
        "cols": COLS,
        "rows": ROWS,
        "frames": frame_rects(),
        "default_clip": "snuggle_idle",
        "clips": clips,
        "library": copy.deepcopy(LIBRARY),
    }


def build(debug: bool = False) -> None:
    clips = [clip for clip in CLIP_ORDER if clip in CLIP_CONFIG]
    frame_counts: dict[str, int] = {}
    page_counts: dict[str, int] = {}
    roots = (APP_STATIC_ROOT, PUBLIC_ROOT)

    for clip in clips:
        frame_paths = _clip_frame_paths(clip)
        frame_counts[clip] = len(frame_paths)
        page_counts[clip] = (len(frame_paths) + CELLS_PER_PAGE - 1) // CELLS_PER_PAGE

        for root in roots:
            _clear_old_outputs(root, clip)
            built_pages = _build_clip_pages(frame_paths, root, clip, debug=debug)
            if built_pages != page_counts[clip]:
                raise RuntimeError(f"Internal page-count mismatch for {clip}: expected {page_counts[clip]}, built {built_pages}")

    meta = _runtime_meta(frame_counts, page_counts)
    for root in roots:
        root.mkdir(parents=True, exist_ok=True)
        (root / "cats_duo_pack.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"built {len(clips)} duo-cat clip pages to {APP_STATIC_ROOT / 'duo_cats'} and {PUBLIC_ROOT / 'duo_cats'}")
    print(f"wrote runtime metadata to {APP_STATIC_ROOT / 'cats_duo_pack.json'} and {PUBLIC_ROOT / 'cats_duo_pack.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build paged 3x2 duo-cat atlases and regenerate runtime metadata.")
    parser.add_argument("--debug", action="store_true", help="also export debug atlases with grid lines")
    args = parser.parse_args()
    build(debug=args.debug)
