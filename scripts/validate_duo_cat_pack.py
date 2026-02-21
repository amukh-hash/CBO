from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageChops

from _duo_cat_pack import (
    APP_STATIC_ROOT,
    ATLAS_H,
    ATLAS_W,
    CELLS_PER_PAGE,
    CLIP_ORDER,
    COLS,
    FRAME_H,
    FRAME_W,
    PUBLIC_ROOT,
    SEAM_CLIPS,
    SOURCE_ROOT,
    clip_frame_count,
)
from duo_pose_scripts import (
    ANCHOR_X,
    ANCHOR_Y,
    CALICO_POSES,
    CONTACT_REQUIRED_CLIPS,
    GRAY_POSES,
    INTERACTION_CLIPS,
    MAX_NON_CONTACT_OVERLAP,
    MAX_OCCLUSION_RATIO,
    MIN_CAT_ALPHA,
    MIN_CONTACT_OVERLAP,
    MIN_VISIBLE_RATIO,
    NON_CONTACT_CLIPS,
    POSE_SCRIPTS,
    CatDirective,
    middle_frame_indices,
    resolve_pose,
    validate_pose_scripts,
)

MIN_ALPHA_PIXELS = 1500
MIN_ADJACENT_DIFF_PIXELS = 200
MIN_SNUGGLE_DISTINCT_FRAMES = 7
INTERACTION_ALLOWED_MIDDLE_REPEATS = 4
FRAME_FILE_RE = re.compile(r"^frame_(\d+)\.png$")


def _alpha_pixel_count(image: Image.Image) -> int:
    alpha_hist = image.getchannel("A").histogram()
    return sum(alpha_hist[1:])


def _overlap_pixel_count(image_a: Image.Image, image_b: Image.Image) -> int:
    alpha_a = image_a.getchannel("A").tobytes()
    alpha_b = image_b.getchannel("A").tobytes()
    if len(alpha_a) != len(alpha_b):
        raise ValueError("Cannot compute overlap for differently sized images")
    overlap = 0
    for idx in range(len(alpha_a)):
        if alpha_a[idx] and alpha_b[idx]:
            overlap += 1
    return overlap


def _diff_pixel_count(image_a: Image.Image, image_b: Image.Image) -> int:
    bytes_a = image_a.tobytes()
    bytes_b = image_b.tobytes()
    if len(bytes_a) != len(bytes_b):
        raise ValueError("Cannot compare frames with different buffer sizes")
    count = 0
    for idx in range(0, len(bytes_a), 4):
        if (
            bytes_a[idx] != bytes_b[idx]
            or bytes_a[idx + 1] != bytes_b[idx + 1]
            or bytes_a[idx + 2] != bytes_b[idx + 2]
            or bytes_a[idx + 3] != bytes_b[idx + 3]
        ):
            count += 1
    return count


def _validate_meta(meta_path: Path) -> dict:
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing metadata: {meta_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    required = ("version", "frameW", "frameH", "cols", "rows", "clips", "default_clip", "library")
    missing = [name for name in required if name not in meta]
    if missing:
        raise ValueError(f"Metadata missing keys: {missing}")
    if meta["version"] != 2:
        raise ValueError(f"Expected metadata version 2, got {meta['version']}")
    if meta["frameW"] != FRAME_W or meta["frameH"] != FRAME_H:
        raise ValueError(f"Expected frame size {FRAME_W}x{FRAME_H}, got {meta['frameW']}x{meta['frameH']}")
    if meta["cols"] != COLS or meta["rows"] != 2:
        raise ValueError(f"Expected atlas grid {COLS}x2, got {meta['cols']}x{meta['rows']}")
    clips = meta.get("clips")
    if not isinstance(clips, dict) or not clips:
        raise ValueError("Metadata clips must be a non-empty object")
    default_clip = meta.get("default_clip")
    if not isinstance(default_clip, str) or default_clip not in clips:
        raise ValueError(f"default_clip '{default_clip}' missing from clips")
    return meta


def _frame_idx(path: Path) -> int:
    match = FRAME_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Invalid source frame file: {path.name}")
    return int(match.group(1))


def _source_frame_paths(clip: str, frame_count: int) -> list[Path]:
    clip_dir = SOURCE_ROOT / clip
    frame_paths = [path for path in clip_dir.glob("frame_*.png") if FRAME_FILE_RE.match(path.name)]
    if not frame_paths:
        raise FileNotFoundError(f"Missing source frames for {clip}: {clip_dir}")
    frame_paths.sort(key=_frame_idx)
    indices = [_frame_idx(path) for path in frame_paths]
    expected = list(range(frame_count))
    if indices != expected:
        raise ValueError(f"{clip} source frame indices must be {expected}, got {indices}")
    return frame_paths


def _validate_sources(clip: str, frame_count: int) -> None:
    frame_paths = _source_frame_paths(clip, frame_count)
    frames = [Image.open(path).convert("RGBA") for path in frame_paths]
    try:
        hashes: list[str] = []
        for idx, frame in enumerate(frames):
            if frame.size != (FRAME_W, FRAME_H):
                raise ValueError(f"{clip} frame_{idx:03d}.png has invalid size {frame.size}")
            hashes.append(hashlib.sha256(frame.tobytes()).hexdigest())
        if clip in SEAM_CLIPS:
            if ImageChops.difference(frames[0], frames[-1]).getbbox() is not None:
                raise ValueError(f"{clip}: source seam broken (frame_000 != last frame)")
        if clip == "snuggle_idle" and len(set(hashes)) < MIN_SNUGGLE_DISTINCT_FRAMES:
            raise ValueError(
                f"{clip}: expected at least {MIN_SNUGGLE_DISTINCT_FRAMES} distinct frames, got {len(set(hashes))}"
            )
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


def _cell_box(cell_idx: int) -> tuple[int, int, int, int]:
    col = cell_idx % COLS
    row = cell_idx // COLS
    x0 = col * FRAME_W
    y0 = row * FRAME_H
    return (x0, y0, x0 + FRAME_W, y0 + FRAME_H)


def _clip_frame_count_from_meta(clip_meta: dict) -> int:
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


def _validate_clip_meta_entry(meta: dict, clip: str, expected_frame_count: int) -> dict:
    if clip not in meta["clips"]:
        raise ValueError(f"Clip '{clip}' missing from metadata")
    clip_meta = meta["clips"][clip]
    if not isinstance(clip_meta, dict):
        raise ValueError(f"Clip '{clip}' metadata must be an object")

    fps = clip_meta.get("fps")
    if not isinstance(fps, (int, float)) or fps <= 0:
        raise ValueError(f"Clip '{clip}' has invalid fps={fps}")
    if not isinstance(clip_meta.get("loop"), bool):
        raise ValueError(f"Clip '{clip}' must include boolean loop")

    frame_count = clip_meta.get("frame_count")
    if not isinstance(frame_count, int) or frame_count <= 0:
        raise ValueError(f"Clip '{clip}' has invalid frame_count={frame_count}")
    if frame_count != expected_frame_count:
        raise ValueError(f"Clip '{clip}' frame_count mismatch: expected {expected_frame_count}, got {frame_count}")

    timeline = clip_meta.get("timeline")
    if not isinstance(timeline, list) or len(timeline) != frame_count:
        raise ValueError(f"Clip '{clip}' timeline length must equal frame_count ({frame_count})")

    pages = clip_meta.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError(f"Clip '{clip}' pages must be a non-empty list")
    for idx, page in enumerate(pages):
        if not isinstance(page, dict):
            raise ValueError(f"Clip '{clip}' page {idx} must be an object")
        image_path = page.get("imagePath")
        if not isinstance(image_path, str) or not image_path:
            raise ValueError(f"Clip '{clip}' page {idx} missing imagePath")

    return clip_meta


def _validate_timeline_and_pages(root: Path, clip: str, clip_meta: dict) -> None:
    pages = clip_meta["pages"]
    timeline = clip_meta["timeline"]
    page_images: list[Image.Image] = []
    page_paths: list[Path] = []

    try:
        for page_idx, page in enumerate(pages):
            atlas_path = _path_from_image_url(root, page["imagePath"])
            page_paths.append(atlas_path)
            if not atlas_path.exists():
                raise FileNotFoundError(f"Missing page atlas for {clip}: {atlas_path}")
            img = Image.open(atlas_path).convert("RGBA")
            if img.size != (ATLAS_W, ATLAS_H):
                raise ValueError(f"{atlas_path} must be {ATLAS_W}x{ATLAS_H}, got {img.size}")
            page_images.append(img)

        frame_hashes: list[str] = []
        frame_images: list[Image.Image] = []
        referenced_cells: set[tuple[int, int]] = set()
        for logical_idx, entry in enumerate(timeline):
            if (
                not isinstance(entry, list)
                or len(entry) != 2
                or not isinstance(entry[0], int)
                or not isinstance(entry[1], int)
            ):
                raise ValueError(f"{clip} timeline entry at index {logical_idx} must be [pageIndex, cellIndex]")
            page_idx, cell_idx = entry
            if page_idx < 0 or page_idx >= len(page_images):
                raise ValueError(f"{clip} timeline[{logical_idx}] invalid pageIndex {page_idx}")
            if cell_idx < 0 or cell_idx >= CELLS_PER_PAGE:
                raise ValueError(f"{clip} timeline[{logical_idx}] invalid cellIndex {cell_idx}")

            frame_img = page_images[page_idx].crop(_cell_box(cell_idx))
            frame_images.append(frame_img)
            frame_hashes.append(hashlib.sha256(frame_img.tobytes()).hexdigest())
            referenced_cells.add((page_idx, cell_idx))

        for page_idx, cell_idx in sorted(referenced_cells):
            cell_img = page_images[page_idx].crop(_cell_box(cell_idx))
            try:
                alpha = _alpha_pixel_count(cell_img)
                if alpha < MIN_ALPHA_PIXELS:
                    page_path = page_paths[page_idx]
                    raise ValueError(
                        f"{page_path} cell {cell_idx} (referenced by {clip}) is mostly empty: "
                        f"alpha>0 pixels={alpha}, min={MIN_ALPHA_PIXELS}"
                    )
            finally:
                cell_img.close()

        if clip == "snuggle_idle":
            distinct = len(set(frame_hashes))
            if distinct < MIN_SNUGGLE_DISTINCT_FRAMES:
                raise ValueError(
                    f"{clip} has only {distinct} distinct timeline frames; "
                    f"requires >= {MIN_SNUGGLE_DISTINCT_FRAMES} with seam frame repeat allowed"
                )

        if clip in INTERACTION_CLIPS:
            middle_hashes = frame_hashes[1:-1]
            required = max(1, len(middle_hashes) - INTERACTION_ALLOWED_MIDDLE_REPEATS)
            if len(set(middle_hashes)) < required:
                raise ValueError(
                    f"{clip} has insufficient middle-frame uniqueness: "
                    f"{len(set(middle_hashes))} distinct, requires >= {required}"
                )

        if clip in SEAM_CLIPS and frame_hashes[0] != frame_hashes[-1]:
            raise ValueError(f"{clip} seam pixels mismatch (first and last timeline frames differ)")

        adjacent_diffs = [_diff_pixel_count(frame_images[idx], frame_images[idx + 1]) for idx in range(len(frame_images) - 1)]
        if adjacent_diffs and max(adjacent_diffs) < MIN_ADJACENT_DIFF_PIXELS:
            raise ValueError(
                f"{clip} has no visible frame deltas in timeline: "
                f"max adjacent diff={max(adjacent_diffs)}, min required={MIN_ADJACENT_DIFF_PIXELS}"
            )
    finally:
        for image in page_images:
            image.close()
        for frame in locals().get("frame_images", []):
            frame.close()


def _load_pose_bank(paths: dict[str, Path], *, cat: str) -> dict[str, Image.Image]:
    loaded: dict[str, Image.Image] = {}
    for key in paths:
        pose_path = resolve_pose(cat, key)
        with Image.open(pose_path) as source:
            loaded[key] = source.convert("RGBA")
    return loaded


def _intersection_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0
    return (x1 - x0) * (y1 - y0)


def _render_cat_layer_for_validation(
    *,
    clip: str,
    frame_idx: int,
    cat: str,
    directive: CatDirective,
    bank: dict[str, Image.Image],
) -> Image.Image:
    pose_key = directive.get("pose")
    if not isinstance(pose_key, str) or not pose_key:
        raise ValueError(f"{clip} frame_{frame_idx} {cat} directive missing pose")

    pose_path = resolve_pose(cat, pose_key)
    source = bank[pose_key]

    flip_x = bool(directive.get("flipX", False))
    transformed = source.transpose(Image.FLIP_LEFT_RIGHT) if flip_x else source

    dx = int(directive.get("dx", 0))
    dy = int(directive.get("dy", 0))
    x = ANCHOR_X + dx
    y = ANCHOR_Y + dy

    alpha_bbox = transformed.getchannel("A").getbbox()
    if alpha_bbox is None:
        raise ValueError(
            f"{clip} frame_{frame_idx} {cat} has no visible alpha after transform: "
            f"pose={pose_key} path={pose_path} dx={dx} dy={dy} flipX={flip_x}"
        )

    local_area = (alpha_bbox[2] - alpha_bbox[0]) * (alpha_bbox[3] - alpha_bbox[1])
    placed_bbox = (
        x + alpha_bbox[0],
        y + alpha_bbox[1],
        x + alpha_bbox[2],
        y + alpha_bbox[3],
    )
    visible_area = _intersection_area(placed_bbox, (0, 0, FRAME_W, FRAME_H))
    if visible_area == 0:
        raise ValueError(
            f"{clip} frame_{frame_idx} {cat} is fully off-canvas: "
            f"pose={pose_key} path={pose_path} dx={dx} dy={dy} flipX={flip_x}"
        )

    visible_ratio = visible_area / float(local_area)
    if visible_ratio < MIN_VISIBLE_RATIO:
        raise ValueError(
            f"{clip} frame_{frame_idx} {cat} mostly off-canvas ({visible_ratio:.3f} visible): "
            f"pose={pose_key} path={pose_path} dx={dx} dy={dy} flipX={flip_x}"
        )

    layer = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    layer.alpha_composite(transformed, (x, y))
    return layer


def _validate_interaction_layers(clip: str, calico_bank: dict[str, Image.Image], gray_bank: dict[str, Image.Image]) -> None:
    if clip not in POSE_SCRIPTS:
        raise ValueError(f"Missing pose script for clip '{clip}'")

    frames = POSE_SCRIPTS[clip]
    expected = clip_frame_count(clip)
    if len(frames) != expected:
        raise ValueError(f"{clip} pose script length mismatch: expected {expected}, got {len(frames)}")

    mid_indices = set(middle_frame_indices(len(frames)))
    mid_overlaps: list[int] = []

    for frame_idx, frame in enumerate(frames):
        calico_directive = frame.get("calico")
        gray_directive = frame.get("gray")

        if clip in INTERACTION_CLIPS and (
            not isinstance(calico_directive, dict) or not isinstance(gray_directive, dict)
        ):
            raise ValueError(f"{clip} frame_{frame_idx} missing calico/gray directives for interaction checks")

        if not isinstance(calico_directive, dict) or not isinstance(gray_directive, dict):
            continue

        calico_layer = _render_cat_layer_for_validation(
            clip=clip,
            frame_idx=frame_idx,
            cat="calico",
            directive=calico_directive,
            bank=calico_bank,
        )
        gray_layer = _render_cat_layer_for_validation(
            clip=clip,
            frame_idx=frame_idx,
            cat="gray",
            directive=gray_directive,
            bank=gray_bank,
        )

        try:
            alpha_cal = _alpha_pixel_count(calico_layer)
            alpha_gray = _alpha_pixel_count(gray_layer)
            overlap = _overlap_pixel_count(calico_layer, gray_layer)

            if clip in INTERACTION_CLIPS:
                if alpha_cal < MIN_CAT_ALPHA:
                    raise ValueError(
                        f"{clip} frame_{frame_idx} calico missing/tiny (alpha={alpha_cal}, min={MIN_CAT_ALPHA})"
                    )
                if alpha_gray < MIN_CAT_ALPHA:
                    raise ValueError(
                        f"{clip} frame_{frame_idx} gray missing/tiny (alpha={alpha_gray}, min={MIN_CAT_ALPHA})"
                    )
                smaller = min(alpha_cal, alpha_gray)
                if smaller > 0:
                    occlusion_ratio = overlap / float(smaller)
                    if occlusion_ratio > MAX_OCCLUSION_RATIO:
                        raise ValueError(
                            f"{clip} frame_{frame_idx} excessive occlusion ({occlusion_ratio:.3f}); "
                            "likely bad offsets or z-order"
                        )

            if frame_idx in mid_indices:
                mid_overlaps.append(overlap)
        finally:
            calico_layer.close()
            gray_layer.close()

    if clip in CONTACT_REQUIRED_CLIPS:
        if not mid_overlaps:
            raise ValueError(f"{clip} has no middle-frame overlap metrics")
        if max(mid_overlaps) < MIN_CONTACT_OVERLAP:
            raise ValueError(
                f"{clip} never reaches contact overlap in middle frames: "
                f"max overlap={max(mid_overlaps)}, min required={MIN_CONTACT_OVERLAP}"
            )

    if clip in NON_CONTACT_CLIPS:
        if not mid_overlaps:
            raise ValueError(f"{clip} has no middle-frame overlap metrics")
        if max(mid_overlaps) > MAX_NON_CONTACT_OVERLAP:
            raise ValueError(
                f"{clip} overlap too high for non-contact clip: "
                f"max overlap={max(mid_overlaps)}, max allowed={MAX_NON_CONTACT_OVERLAP}"
            )


def _validate_library(meta: dict) -> None:
    clips = meta.get("clips", {})
    library = meta.get("library")
    if not isinstance(library, dict):
        raise ValueError("library must be an object")

    foundation = library.get("foundation")
    if not isinstance(foundation, str) or foundation not in clips:
        raise ValueError(f"library.foundation '{foundation}' is missing from clips")
    foundation_clip = clips[foundation]
    if not isinstance(foundation_clip.get("loop"), bool) or foundation_clip["loop"] is not True:
        raise ValueError(f"library.foundation '{foundation}' must be loop=true")

    groups = library.get("groups", {})
    if not isinstance(groups, dict):
        raise ValueError("library.groups must be an object")
    for group_name, group_clips in groups.items():
        if not isinstance(group_clips, list):
            raise ValueError(f"library.groups.{group_name} must be a list")
        for clip in group_clips:
            if clip not in clips:
                raise ValueError(f"library.groups.{group_name} references unknown clip '{clip}'")

    playlists = library.get("playlists", {})
    if not isinstance(playlists, dict):
        raise ValueError("library.playlists must be an object")
    for playlist_name, playlist in playlists.items():
        if not isinstance(playlist, dict):
            raise ValueError(f"library.playlists.{playlist_name} must be an object")
        idle_clip = playlist.get("idle_clip", foundation)
        if not isinstance(idle_clip, str) or idle_clip not in clips:
            raise ValueError(f"Playlist '{playlist_name}' has invalid idle_clip '{idle_clip}'")

        mode = playlist.get("mode")
        if mode == "sequence":
            values = playlist.get("clips")
            if not isinstance(values, list) or not values:
                raise ValueError(f"Playlist '{playlist_name}' sequence clips must be a non-empty list")
            for clip in values:
                if clip not in clips:
                    raise ValueError(f"Playlist '{playlist_name}' references unknown clip '{clip}'")
        elif mode == "weighted_random":
            pool = playlist.get("pool")
            if not isinstance(pool, list) or not pool:
                raise ValueError(f"Playlist '{playlist_name}' pool must be a non-empty list")
            for pair in pool:
                if not isinstance(pair, list) or len(pair) != 2:
                    raise ValueError(f"Playlist '{playlist_name}' pool entries must be [clip, weight]")
                clip, weight = pair
                if clip not in clips:
                    raise ValueError(f"Playlist '{playlist_name}' references unknown clip '{clip}'")
                if not isinstance(weight, (int, float)) or weight <= 0:
                    raise ValueError(f"Playlist '{playlist_name}' has invalid weight '{weight}' for clip '{clip}'")
        else:
            raise ValueError(f"Playlist '{playlist_name}' has unsupported mode '{mode}'")


def _validate_outputs(root: Path, clip: str, clip_meta: dict) -> None:
    gif = root / "duo_cats_gifs" / f"{clip}.gif"
    if not gif.exists():
        raise FileNotFoundError(f"Missing GIF: {gif}")
    _validate_timeline_and_pages(root, clip, clip_meta)


def validate() -> None:
    validate_pose_scripts(CLIP_ORDER, {clip: clip_frame_count(clip) for clip in CLIP_ORDER})

    app_meta = _validate_meta(APP_STATIC_ROOT / "cats_duo_pack.json")
    public_meta = _validate_meta(PUBLIC_ROOT / "cats_duo_pack.json")
    _validate_library(app_meta)
    _validate_library(public_meta)

    calico_bank = _load_pose_bank(CALICO_POSES, cat="calico")
    gray_bank = _load_pose_bank(GRAY_POSES, cat="gray")

    try:
        for clip in CLIP_ORDER:
            expected_frame_count = clip_frame_count(clip)
            _validate_sources(clip, expected_frame_count)
            _validate_interaction_layers(clip, calico_bank, gray_bank)

            app_clip_meta = _validate_clip_meta_entry(app_meta, clip, expected_frame_count)
            public_clip_meta = _validate_clip_meta_entry(public_meta, clip, expected_frame_count)

            if app_clip_meta != public_clip_meta:
                raise ValueError(f"Clip '{clip}' metadata differs between app and public outputs")

            _validate_outputs(APP_STATIC_ROOT, clip, app_clip_meta)
            _validate_outputs(PUBLIC_ROOT, clip, public_clip_meta)

        foundation = app_meta["library"]["foundation"]
        if foundation not in app_meta["clips"] or app_meta["clips"][foundation]["loop"] is not True:
            raise ValueError(f"Foundation clip '{foundation}' missing or not loop=true")
    finally:
        for bank in (calico_bank, gray_bank):
            for image in bank.values():
                image.close()

    print("duo-cat pack validation passed")


if __name__ == "__main__":
    validate()
