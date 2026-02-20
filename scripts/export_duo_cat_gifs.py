from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from _duo_cat_pack import APP_STATIC_ROOT, CLIP_ORDER, PUBLIC_ROOT, SOURCE_ROOT, TOTAL_FRAMES


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


def _export_clip(clip: str, duration_ms: int, out_path: Path, loop_count: int) -> None:
    clip_dir = SOURCE_ROOT / clip
    frame_paths = [clip_dir / f"frame_{idx}.png" for idx in range(TOTAL_FRAMES)]
    missing = [str(path) for path in frame_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing source frame(s) for {clip}: {', '.join(missing)}")

    frames = [Image.open(path).convert("RGBA") for path in frame_paths]
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(
            out_path,
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


def export() -> None:
    meta = _load_meta()
    app_out = APP_STATIC_ROOT / "duo_cats_gifs"
    public_out = PUBLIC_ROOT / "duo_cats_gifs"
    for clip in CLIP_ORDER:
        duration_ms = _clip_duration_ms(meta, clip)
        loop_count = 0 if clip == "snuggle_idle" else 1
        _export_clip(clip, duration_ms, app_out / f"{clip}.gif", loop_count)
        _export_clip(clip, duration_ms, public_out / f"{clip}.gif", loop_count)
    print(f"exported {len(CLIP_ORDER)} GIFs to {app_out} and {public_out}")


if __name__ == "__main__":
    export()

