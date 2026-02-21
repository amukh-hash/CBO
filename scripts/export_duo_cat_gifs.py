from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image

from _duo_cat_pack import APP_STATIC_ROOT, CLIP_ORDER, PUBLIC_ROOT, SOURCE_ROOT

FRAME_FILE_RE = re.compile(r"^frame_(\d+)\.png$")


def _load_meta() -> dict:
    meta_path = APP_STATIC_ROOT / "cats_duo_pack.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing runtime metadata: {meta_path}. Run build_duo_cat_atlases.py first.")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _clip_duration_ms(meta: dict, clip: str) -> int:
    clip_meta = meta.get("clips", {}).get(clip, {})
    fps = clip_meta.get("fps", 6)
    if not isinstance(fps, (int, float)) or fps <= 0:
        fps = 6
    return max(1, int(round(1000 / fps)))


def _clip_frame_count(meta: dict, clip: str) -> int:
    clip_meta = meta.get("clips", {}).get(clip, {})
    timeline = clip_meta.get("timeline")
    if isinstance(timeline, list) and timeline:
        return len(timeline)
    frame_count = clip_meta.get("frame_count")
    if isinstance(frame_count, int) and frame_count > 0:
        return frame_count
    frames = clip_meta.get("frames")
    if isinstance(frames, list) and frames:
        return len(frames)
    return 0


def _frame_idx(path: Path) -> int:
    match = FRAME_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Invalid frame filename: {path.name}")
    return int(match.group(1))


def _source_frames(clip: str, frame_count: int) -> list[Path]:
    clip_dir = SOURCE_ROOT / clip
    frame_paths = [path for path in clip_dir.glob("frame_*.png") if FRAME_FILE_RE.match(path.name)]
    if not frame_paths:
        raise FileNotFoundError(f"Missing source frames for {clip} in {clip_dir}")
    frame_paths.sort(key=_frame_idx)
    expected_indices = list(range(frame_count))
    actual_indices = [_frame_idx(path) for path in frame_paths[:frame_count]]
    if actual_indices != expected_indices:
        raise ValueError(f"{clip} source frame indices do not match expected range 0..{frame_count - 1}: {actual_indices}")
    if len(frame_paths) < frame_count:
        raise FileNotFoundError(f"{clip} expected {frame_count} source frames, found {len(frame_paths)}")
    return frame_paths[:frame_count]


def export() -> None:
    meta = _load_meta()
    app_out = APP_STATIC_ROOT / "duo_cats_gifs"
    public_out = PUBLIC_ROOT / "duo_cats_gifs"
    for clip in CLIP_ORDER:
        duration_ms = _clip_duration_ms(meta, clip)
        loop_count = 0 if clip == "snuggle_idle" else 1
        frame_count = _clip_frame_count(meta, clip)
        if frame_count <= 0:
            raise ValueError(f"Invalid frame_count for clip '{clip}' in metadata")
        frame_paths = _source_frames(clip, frame_count)
        frames = [Image.open(path).convert("RGBA") for path in frame_paths]
        try:
            app_path = app_out / f"{clip}.gif"
            app_path.parent.mkdir(parents=True, exist_ok=True)
            frames[0].save(
                app_path,
                save_all=True,
                append_images=frames[1:],
                optimize=False,
                duration=duration_ms,
                disposal=2,
                transparency=0,
                loop=loop_count,
            )
            public_path = public_out / f"{clip}.gif"
            public_path.parent.mkdir(parents=True, exist_ok=True)
            frames[0].save(
                public_path,
                save_all=True,
                append_images=frames[1:],
                optimize=False,
                duration=duration_ms,
                disposal=2,
                transparency=0,
                loop=loop_count,
            )
        finally:
            for frame in frames:
                frame.close()
    print(f"exported {len(CLIP_ORDER)} GIFs to {app_out} and {public_out}")


if __name__ == "__main__":
    export()
