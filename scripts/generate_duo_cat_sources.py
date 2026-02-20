from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from _duo_cat_pack import FRAME_H, FRAME_W, CLIP_ORDER, SOURCE_ROOT

BASE_BOARD = Path("app/ui/static/catsCBO.png")
FALLBACK_ATLAS = Path("app/ui/static/sprites/cats/cats_duo_atlas.png")


def _crop_pose(board: Image.Image, cx: int, cy: int, w: int = 310, h: int = 190) -> Image.Image:
    x0 = max(0, cx - (w // 2))
    y0 = max(0, cy - (h // 2))
    x1 = min(board.width, x0 + w)
    y1 = min(board.height, y0 + h)
    return board.crop((x0, y0, x1, y1))


def _extract_cells_from_board(board: Image.Image) -> dict[str, Image.Image]:
    # Centers tuned for app/ui/static/catsCBO.png (1024x1536).
    return {
        "gr0": _crop_pose(board, 176, 560),   # Manual grooming
        "gr1": _crop_pose(board, 512, 560),   # Nose boop / greeting
        "pl0": _crop_pose(board, 176, 740),   # Play pounce
        "pl1": _crop_pose(board, 512, 740),   # Paw batting
        "sn": _crop_pose(board, 512, 1470),   # Snuggle idle (bottom center)
        "sn_b": _crop_pose(board, 846, 560),  # Snuggle / curl together
        "chase": _crop_pose(board, 846, 1088),
        "kick": _crop_pose(board, 176, 914),
        "swat": _crop_pose(board, 512, 914),
        "standoff": _crop_pose(board, 846, 914),
        "clash": _crop_pose(board, 176, 1262),
        "ear": _crop_pose(board, 512, 1262),
        "face": _crop_pose(board, 846, 1262),
    }


def _extract_cells_from_fallback_atlas(atlas: Image.Image) -> dict[str, Image.Image]:
    cells: list[Image.Image] = []
    for idx in range(6):
        x = (idx % 3) * FRAME_W
        y = (idx // 3) * FRAME_H
        cells.append(atlas.crop((x, y, x + FRAME_W, y + FRAME_H)))
    return {
        "gr0": cells[0],
        "gr1": cells[1],
        "pl0": cells[2],
        "pl1": cells[3],
        "sn": cells[4],
        "sn_b": cells[5],
        "chase": cells[3],
        "kick": cells[2],
        "swat": cells[1],
        "standoff": cells[0],
        "clash": cells[2],
        "ear": cells[1],
        "face": cells[0],
    }


def _compose(
    base: Image.Image,
    *,
    dx: int = 0,
    dy: int = 0,
    sx: float = 1.0,
    sy: float = 1.0,
    mirror: bool = False,
    motion: str = "",
) -> Image.Image:
    frame = base.copy()
    if mirror:
        frame = ImageOps.mirror(frame)

    if sx != 1.0 or sy != 1.0:
        new_w = max(1, int(round(frame.width * sx)))
        new_h = max(1, int(round(frame.height * sy)))
        frame = frame.resize((new_w, new_h), Image.Resampling.NEAREST)

    canvas = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    x = (FRAME_W - frame.width) // 2 + dx
    y = (FRAME_H - frame.height) // 2 + dy
    canvas.alpha_composite(frame, (x, y))

    if motion:
        draw = ImageDraw.Draw(canvas)
        color = (255, 255, 255, 120)
        if motion == "paw":
            draw.line((364, 112, 432, 94), fill=color, width=2)
            draw.line((362, 126, 438, 112), fill=color, width=2)
        elif motion == "pounce":
            draw.line((80, 88, 42, 78), fill=color, width=2)
            draw.line((96, 102, 56, 92), fill=color, width=2)
        elif motion == "clash":
            draw.line((196, 90, 256, 56), fill=color, width=2)
            draw.line((312, 90, 260, 56), fill=color, width=2)
            draw.line((252, 132, 252, 78), fill=color, width=2)
        elif motion == "chase":
            draw.line((72, 172, 24, 162), fill=color, width=2)
            draw.line((460, 170, 500, 156), fill=color, width=2)
        elif motion == "boop":
            draw.line((240, 114, 278, 108), fill=color, width=2)
        elif motion == "kick":
            draw.line((412, 150, 466, 146), fill=color, width=2)
            draw.line((412, 164, 470, 164), fill=color, width=2)
    return canvas


def _recipes(cells: dict[str, Image.Image]) -> dict[str, list[Image.Image]]:
    sn = cells["sn"]
    sn_b = cells["sn_b"]
    gr0 = cells["gr0"]
    gr1 = cells["gr1"]
    pl0 = cells["pl0"]
    pl1 = cells["pl1"]
    chase = cells["chase"]
    kick = cells["kick"]
    swat = cells["swat"]
    standoff = cells["standoff"]
    clash = cells["clash"]
    ear = cells["ear"]
    face = cells["face"]
    sn0 = _compose(sn)
    gr00 = _compose(gr0)
    gr10 = _compose(gr1)

    # Frame 0 and frame 5 are identical snuggle for every clip.
    return {
        "snuggle_idle": [
            sn0,
            _compose(sn, dy=1, sy=1.01),
            _compose(sn_b, dy=0, sy=0.99),
            _compose(sn_b, dy=-1, sy=0.99),
            _compose(sn, dy=0, sy=1.01),
            sn0,
        ],
        "mutual_groom": [
            sn0,
            _compose(gr0, dy=-1),
            _compose(gr1, dy=0),
            _compose(gr0, dy=-1),
            _compose(gr1, dy=0),
            sn0,
        ],
        "nose_boop": [
            sn0,
            _compose(gr0, dx=1, motion="boop"),
            _compose(gr1, dx=3, motion="boop"),
            _compose(gr0, dx=2, motion="boop"),
            gr10,
            sn0,
        ],
        "snuggle_curl": [
            sn0,
            _compose(sn_b, dy=2, sy=0.98),
            _compose(sn_b, dy=3, sy=0.97),
            _compose(sn_b, dy=2, sy=0.98),
            _compose(sn, dy=1, sy=1.0),
            sn0,
        ],
        "play_pounce": [
            sn0,
            _compose(pl0, dx=-5, motion="pounce"),
            _compose(pl1, dx=5, motion="pounce"),
            _compose(pl0, dx=3),
            _compose(pl1, dx=-2),
            sn0,
        ],
        "paw_batting": [
            sn0,
            _compose(gr0, dx=-3, motion="paw"),
            _compose(pl0, dx=2, motion="paw"),
            _compose(gr1, dx=1, motion="paw"),
            gr00,
            sn0,
        ],
        "chase_loop": [
            sn0,
            _compose(chase, dx=-10, motion="chase"),
            _compose(chase, dx=8, motion="chase"),
            _compose(chase, dx=6, motion="chase"),
            _compose(chase, dx=-8, motion="chase"),
            sn0,
        ],
        "bunny_kick": [
            sn0,
            _compose(kick, dy=-1, motion="kick"),
            _compose(kick, dy=2, motion="kick"),
            _compose(kick, dy=1, motion="kick"),
            _compose(kick, dy=1),
            sn0,
        ],
        "standing_swat": [
            sn0,
            _compose(swat, dy=-6, sy=1.03),
            _compose(swat, dy=-4, sy=1.02),
            _compose(swat, dy=-2),
            _compose(swat, dy=-3, motion="paw"),
            sn0,
        ],
        "standoff": [
            sn0,
            _compose(standoff, dx=-5),
            _compose(standoff, dx=5),
            _compose(standoff, dy=-1),
            _compose(standoff, dx=0),
            sn0,
        ],
        "explosive_clash": [
            sn0,
            _compose(clash, dx=-7, motion="clash"),
            _compose(clash, dx=7, motion="clash"),
            _compose(clash, motion="clash"),
            _compose(clash, dx=-2, motion="clash"),
            sn0,
        ],
        "ear_cleaning": [
            sn0,
            _compose(ear, dy=-1),
            _compose(ear, dy=0),
            _compose(ear, dy=1),
            _compose(ear, dy=0),
            sn0,
        ],
        "face_wash_assist": [
            sn0,
            _compose(face, dy=0),
            _compose(face, dy=1),
            _compose(face, dy=0),
            _compose(face, dy=0),
            sn0,
        ],
    }


def generate() -> None:
    if BASE_BOARD.exists():
        with Image.open(BASE_BOARD) as board:
            board_rgba = board.convert("RGBA")
            named_cells = _extract_cells_from_board(board_rgba)
    elif FALLBACK_ATLAS.exists():
        with Image.open(FALLBACK_ATLAS) as atlas:
            atlas_rgba = atlas.convert("RGBA")
            named_cells = _extract_cells_from_fallback_atlas(atlas_rgba)
    else:
        raise FileNotFoundError(f"Missing source images: {BASE_BOARD} and fallback {FALLBACK_ATLAS}")

    clip_frames = _recipes(named_cells)

    for clip in CLIP_ORDER:
        out_dir = SOURCE_ROOT / clip
        out_dir.mkdir(parents=True, exist_ok=True)
        frames = clip_frames[clip]
        if len(frames) != 6:
            raise ValueError(f"{clip} must have exactly 6 frames, got {len(frames)}")
        for idx, frame in enumerate(frames):
            frame.save(out_dir / f"frame_{idx}.png")

    print(f"generated source frames under {SOURCE_ROOT}")


if __name__ == "__main__":
    generate()
