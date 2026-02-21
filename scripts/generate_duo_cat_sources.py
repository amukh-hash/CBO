from __future__ import annotations

import argparse
from pathlib import Path
from typing import Mapping

from PIL import Image, ImageDraw

from _duo_cat_pack import CLIP_ORDER, FRAME_H, FRAME_W, SOURCE_ROOT, clip_frame_count
from duo_pose_scripts import (
    ANCHOR_X,
    ANCHOR_Y,
    CALICO_POSES,
    CONTACT_REQUIRED_CLIPS,
    DEFAULT_Z_ORDER,
    GRAY_POSES,
    INTERACTION_CLIPS,
    MIN_CAT_ALPHA,
    MIN_VISIBLE_RATIO,
    PAIR_POSES,
    POSE_SCRIPTS,
    VALID_Z_ORDERS,
    CatDirective,
    FrameDirective,
    OverlayDirective,
    resolve_pair_pose,
    resolve_pose,
    validate_pose_scripts,
)

OVERLAY_W = 126
OVERLAY_H = 86


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


def _load_pose_bank(paths: Mapping[str, Path], *, kind: str) -> dict[str, Image.Image]:
    loaded: dict[str, Image.Image] = {}
    for key in paths:
        if kind == "calico":
            pose_path = resolve_pose("calico", key)
        elif kind == "gray":
            pose_path = resolve_pose("gray", key)
        elif kind == "pair":
            pose_path = resolve_pair_pose(key)
        else:
            raise ValueError(f"Unsupported pose bank kind '{kind}'")

        with Image.open(pose_path) as source:
            loaded[key] = source.convert("RGBA")
    return loaded


def _overlay_xy(x: int, y: int, *, origin_x: int, origin_y: int, flip_x: bool) -> tuple[int, int]:
    px = (OVERLAY_W - 1 - x) if flip_x else x
    py = y
    return origin_x + px, origin_y + py


def _draw_overlay(canvas: Image.Image, overlay: OverlayDirective) -> None:
    name = overlay.get("name")
    if not name:
        raise ValueError("Overlay directive missing required 'name'")

    origin_x = ANCHOR_X + int(overlay.get("dx", 0))
    origin_y = ANCHOR_Y + int(overlay.get("dy", 0))
    flip_x = bool(overlay.get("flipX", False))

    draw = ImageDraw.Draw(canvas)
    stroke = (255, 255, 255, 140)
    accent = (255, 230, 170, 120)

    def line(x0: int, y0: int, x1: int, y1: int, *, width: int = 2, color: tuple[int, int, int, int] = stroke) -> None:
        ax, ay = _overlay_xy(x0, y0, origin_x=origin_x, origin_y=origin_y, flip_x=flip_x)
        bx, by = _overlay_xy(x1, y1, origin_x=origin_x, origin_y=origin_y, flip_x=flip_x)
        draw.line((ax, ay, bx, by), fill=color, width=width)

    def ring(cx: int, cy: int, radius: int, *, color: tuple[int, int, int, int] = accent) -> None:
        x, y = _overlay_xy(cx, cy, origin_x=origin_x, origin_y=origin_y, flip_x=flip_x)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, width=1)

    if name == "boop_ping":
        line(61, 27, 67, 27, width=2)
        line(64, 24, 64, 30, width=2)
        ring(64, 27, 5)
    elif name == "paw_contact":
        line(56, 42, 74, 36)
        line(58, 47, 76, 42)
        line(61, 51, 79, 48)
    elif name == "lick_left":
        line(54, 28, 46, 31)
        line(52, 31, 44, 33, color=accent)
    elif name == "lick_right":
        line(66, 28, 74, 31)
        line(68, 31, 76, 33, color=accent)
    elif name == "pounce_trail":
        line(24, 58, 54, 44)
        line(18, 62, 48, 48)
        line(12, 66, 42, 52)
    elif name == "impact_star":
        line(58, 34, 70, 46)
        line(58, 46, 70, 34)
        line(64, 30, 64, 50)
        line(54, 40, 74, 40)
    elif name == "kick_blur":
        line(70, 56, 92, 54)
        line(68, 61, 95, 61)
    elif name == "clash_burst":
        line(62, 30, 62, 50)
        line(52, 40, 72, 40)
        line(54, 32, 70, 48)
        line(54, 48, 70, 32)
    elif name == "ear_twitch":
        line(72, 9, 78, 4)
        line(76, 8, 83, 3)
    elif name == "tail_flick":
        line(92, 49, 104, 42)
        line(95, 54, 109, 49)
    elif name == "curl_swish":
        line(84, 62, 102, 70)
        line(80, 66, 98, 74)
    elif name == "chase_arc":
        line(36, 60, 56, 48)
        line(56, 48, 78, 52)
        line(78, 52, 94, 40)
    else:
        raise ValueError(f"Unknown overlay '{name}'")


def _alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("Transformed layer has no visible pixels")
    return bbox


def _intersection_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0
    return (x1 - x0) * (y1 - y0)


def _assert_layer_bounds(
    *,
    clip: str,
    frame_idx: int,
    cat: str,
    pose_key: str,
    pose_path: Path,
    dx: int,
    dy: int,
    flip_x: bool,
    transformed: Image.Image,
    x: int,
    y: int,
) -> None:
    local_bbox = _alpha_bbox(transformed)
    local_area = (local_bbox[2] - local_bbox[0]) * (local_bbox[3] - local_bbox[1])
    placed_bbox = (
        x + local_bbox[0],
        y + local_bbox[1],
        x + local_bbox[2],
        y + local_bbox[3],
    )
    frame_bbox = (0, 0, FRAME_W, FRAME_H)
    visible_area = _intersection_area(placed_bbox, frame_bbox)
    if visible_area == 0:
        raise ValueError(
            f"{clip} frame_{frame_idx} {cat} layer off-canvas: "
            f"pose={pose_key} path={pose_path} dx={dx} dy={dy} flipX={flip_x} bbox={placed_bbox}"
        )
    visible_ratio = visible_area / float(local_area)
    if visible_ratio < MIN_VISIBLE_RATIO:
        raise ValueError(
            f"{clip} frame_{frame_idx} {cat} layer mostly off-canvas ({visible_ratio:.3f} visible): "
            f"pose={pose_key} path={pose_path} dx={dx} dy={dy} flipX={flip_x} bbox={placed_bbox}"
        )


def _render_cat_layer(
    *,
    clip: str,
    frame_idx: int,
    cat: str,
    directive: CatDirective,
    calico_bank: Mapping[str, Image.Image],
    gray_bank: Mapping[str, Image.Image],
) -> tuple[Image.Image, str, Path, int, int, bool, int]:
    pose_key = directive.get("pose")
    if not isinstance(pose_key, str) or not pose_key:
        raise ValueError(f"{clip} frame_{frame_idx} {cat} directive missing pose")

    if cat == "calico":
        pose_path = resolve_pose("calico", pose_key)
        source = calico_bank[pose_key]
    elif cat == "gray":
        pose_path = resolve_pose("gray", pose_key)
        source = gray_bank[pose_key]
    else:
        raise ValueError(f"Unsupported cat id '{cat}'")

    flip_x = bool(directive.get("flipX", False))
    transformed = source.transpose(Image.FLIP_LEFT_RIGHT) if flip_x else source

    dx = int(directive.get("dx", 0))
    dy = int(directive.get("dy", 0))
    x = ANCHOR_X + dx
    y = ANCHOR_Y + dy

    _assert_layer_bounds(
        clip=clip,
        frame_idx=frame_idx,
        cat=cat,
        pose_key=pose_key,
        pose_path=pose_path,
        dx=dx,
        dy=dy,
        flip_x=flip_x,
        transformed=transformed,
        x=x,
        y=y,
    )

    layer = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    layer.alpha_composite(transformed, (x, y))
    alpha = _alpha_pixel_count(layer)

    return layer, pose_key, pose_path, dx, dy, flip_x, alpha


def _resolve_z_order(clip: str, frame_idx: int, directive: FrameDirective) -> tuple[str, str]:
    raw = directive.get("z_order")
    if raw is None:
        return DEFAULT_Z_ORDER
    if not isinstance(raw, list) or tuple(raw) not in VALID_Z_ORDERS:
        raise ValueError(
            f"{clip} frame_{frame_idx} has invalid z_order={raw}; expected one of {sorted(VALID_Z_ORDERS)}"
        )
    return raw[0], raw[1]


def _compose_with_z_order(
    *,
    z_order: tuple[str, str],
    calico_layer: Image.Image,
    gray_layer: Image.Image,
) -> Image.Image:
    combined = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    first = calico_layer if z_order[0] == "calico" else gray_layer
    second = gray_layer if z_order[1] == "gray" else calico_layer
    combined.alpha_composite(first)
    combined.alpha_composite(second)
    return combined


def _print_frame_log(
    *,
    clip: str,
    frame_idx: int,
    cal_pose: str,
    cal_path: Path | None,
    cal_dx: int,
    cal_dy: int,
    cal_flip: bool,
    gray_pose: str,
    gray_path: Path | None,
    gray_dx: int,
    gray_dy: int,
    gray_flip: bool,
    pair_path: Path | None,
    order: str,
    alpha_cal: int,
    alpha_gray: int,
    overlap: int,
) -> None:
    print(
        f"[DUO_GEN] clip={clip} i={frame_idx} "
        f"CAL pose={cal_pose} path={cal_path or 'none'} dx={cal_dx} dy={cal_dy} flipX={cal_flip} "
        f"GRY pose={gray_pose} path={gray_path or 'none'} dx={gray_dx} dy={gray_dy} flipX={gray_flip} "
        f"pair_pose={pair_path or 'none'} order={order} "
        f"alpha_cal={alpha_cal} alpha_gry={alpha_gray} overlap={overlap}"
    )


def _clear_existing_frames(out_dir: Path) -> None:
    for path in out_dir.glob("frame_*.png"):
        path.unlink()
    for suffix in (".calico_only.png", ".gray_only.png", ".combined.png"):
        for path in out_dir.glob(f"frame_*{suffix}"):
            path.unlink()


def generate(*, debug: bool = False, verbose: bool = False) -> None:
    validate_pose_scripts(CLIP_ORDER, {clip: clip_frame_count(clip) for clip in CLIP_ORDER})

    calico_bank = _load_pose_bank(CALICO_POSES, kind="calico")
    gray_bank = _load_pose_bank(GRAY_POSES, kind="gray")
    pair_bank = _load_pose_bank(PAIR_POSES, kind="pair")

    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)

    try:
        for clip in CLIP_ORDER:
            out_dir = SOURCE_ROOT / clip
            out_dir.mkdir(parents=True, exist_ok=True)
            _clear_existing_frames(out_dir)

            directives = POSE_SCRIPTS[clip]
            expected_frames = clip_frame_count(clip)
            if len(directives) != expected_frames:
                raise ValueError(f"{clip} script length {len(directives)} does not match frame_count {expected_frames}")
            for frame_idx, directive in enumerate(directives):
                pair_pose_key = directive.get("pair_pose")
                pair_path: Path | None = None

                cal_pose = "none"
                gray_pose = "none"
                cal_path: Path | None = None
                gray_path: Path | None = None
                cal_dx = 0
                cal_dy = 0
                gray_dx = 0
                gray_dy = 0
                cal_flip = False
                gray_flip = False

                calico_layer = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
                gray_layer = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
                combined = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))

                try:
                    calico_directive = directive.get("calico")
                    gray_directive = directive.get("gray")

                    if isinstance(calico_directive, dict):
                        (
                            calico_layer,
                            cal_pose,
                            cal_path,
                            cal_dx,
                            cal_dy,
                            cal_flip,
                            _,
                        ) = _render_cat_layer(
                            clip=clip,
                            frame_idx=frame_idx,
                            cat="calico",
                            directive=calico_directive,
                            calico_bank=calico_bank,
                            gray_bank=gray_bank,
                        )

                    if isinstance(gray_directive, dict):
                        (
                            gray_layer,
                            gray_pose,
                            gray_path,
                            gray_dx,
                            gray_dy,
                            gray_flip,
                            _,
                        ) = _render_cat_layer(
                            clip=clip,
                            frame_idx=frame_idx,
                            cat="gray",
                            directive=gray_directive,
                            calico_bank=calico_bank,
                            gray_bank=gray_bank,
                        )

                    if clip in INTERACTION_CLIPS:
                        if not isinstance(calico_directive, dict) or not isinstance(gray_directive, dict):
                            raise ValueError(f"{clip} frame_{frame_idx} requires both calico and gray directives")

                    if pair_pose_key:
                        if not isinstance(pair_pose_key, str) or not pair_pose_key:
                            raise ValueError(f"{clip} frame_{frame_idx} has invalid pair_pose={pair_pose_key}")
                        pair_path = resolve_pair_pose(pair_pose_key)
                        pair_img = pair_bank[pair_pose_key]
                        pair_flip = bool(directive.get("flipX", False))
                        transformed_pair = pair_img.transpose(Image.FLIP_LEFT_RIGHT) if pair_flip else pair_img
                        pair_x = ANCHOR_X + int(directive.get("dx", 0))
                        pair_y = ANCHOR_Y + int(directive.get("dy", 0))
                        combined.alpha_composite(transformed_pair, (pair_x, pair_y))
                        paste_order = "pair_pose"
                    else:
                        if not isinstance(calico_directive, dict) or not isinstance(gray_directive, dict):
                            raise ValueError(
                                f"{clip} frame_{frame_idx} must define pair_pose or both calico+gray directives"
                            )
                        z_order = _resolve_z_order(clip, frame_idx, directive)
                        combined = _compose_with_z_order(
                            z_order=z_order,
                            calico_layer=calico_layer,
                            gray_layer=gray_layer,
                        )
                        paste_order = f"{z_order[0]}->{z_order[1]}"

                    for overlay in directive.get("overlays", []):
                        _draw_overlay(combined, overlay)

                    alpha_cal = _alpha_pixel_count(calico_layer)
                    alpha_gray = _alpha_pixel_count(gray_layer)
                    overlap = _overlap_pixel_count(calico_layer, gray_layer)

                    if clip in CONTACT_REQUIRED_CLIPS:
                        if alpha_cal < MIN_CAT_ALPHA:
                            raise ValueError(
                                f"{clip} frame_{frame_idx} calico alpha too small ({alpha_cal} < {MIN_CAT_ALPHA})"
                            )
                        if alpha_gray < MIN_CAT_ALPHA:
                            raise ValueError(
                                f"{clip} frame_{frame_idx} gray alpha too small ({alpha_gray} < {MIN_CAT_ALPHA})"
                            )

                    out_base = out_dir / f"frame_{frame_idx:03d}"
                    combined.save(out_base.with_suffix(".png"))
                    if debug:
                        calico_layer.save(out_base.with_suffix(".calico_only.png"))
                        gray_layer.save(out_base.with_suffix(".gray_only.png"))
                        combined.save(out_base.with_suffix(".combined.png"))

                    if verbose or debug:
                        _print_frame_log(
                            clip=clip,
                            frame_idx=frame_idx,
                            cal_pose=cal_pose,
                            cal_path=cal_path,
                            cal_dx=cal_dx,
                            cal_dy=cal_dy,
                            cal_flip=cal_flip,
                            gray_pose=gray_pose,
                            gray_path=gray_path,
                            gray_dx=gray_dx,
                            gray_dy=gray_dy,
                            gray_flip=gray_flip,
                            pair_path=pair_path,
                            order=paste_order,
                            alpha_cal=alpha_cal,
                            alpha_gray=alpha_gray,
                            overlap=overlap,
                        )
                finally:
                    calico_layer.close()
                    gray_layer.close()
                    combined.close()
    finally:
        for bank in (calico_bank, gray_bank, pair_bank):
            for image in bank.values():
                image.close()

    print(f"generated source frames under {SOURCE_ROOT}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate duo-cat source frames from strict pose scripts")
    parser.add_argument("--debug", action="store_true", help="write per-frame calico_only/gray_only/combined debug images")
    parser.add_argument("--verbose", action="store_true", help="print per-frame resolved pose and alpha diagnostics")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    generate(debug=args.debug, verbose=args.verbose)
