from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from _duo_cat_pack import FRAME_H, FRAME_W, CLIP_ORDER, SOURCE_ROOT

BASE_ATLAS = Path("app/ui/static/sprites/cats/cats_duo_atlas.png")


def _extract_cells(atlas: Image.Image) -> list[Image.Image]:
    cells: list[Image.Image] = []
    for idx in range(6):
        x = (idx % 3) * FRAME_W
        y = (idx // 3) * FRAME_H
        cells.append(atlas.crop((x, y, x + FRAME_W, y + FRAME_H)))
    return cells


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

    # Frame 0 and frame 5 are identical snuggle for every clip.
    return {
        "snuggle_idle": [
            sn,
            _compose(sn, dy=1, sy=1.01),
            _compose(sn_b, dy=0, sy=0.99),
            _compose(sn_b, dy=-1, sy=0.99),
            _compose(sn, dy=0, sy=1.01),
            sn,
        ],
        "mutual_groom": [
            sn,
            _compose(gr0, dy=-1),
            _compose(gr1, dy=0),
            _compose(gr0, dy=-1),
            _compose(gr1, dy=0),
            sn,
        ],
        "nose_boop": [
            sn,
            _compose(gr0, dx=1, motion="boop"),
            _compose(gr1, dx=3, motion="boop"),
            _compose(gr0, dx=2, motion="boop"),
            _compose(gr1, dx=0),
            sn,
        ],
        "snuggle_curl": [
            sn,
            _compose(sn_b, dy=2, sy=0.98),
            _compose(sn_b, dy=3, sy=0.97),
            _compose(sn_b, dy=2, sy=0.98),
            _compose(sn, dy=1, sy=1.0),
            sn,
        ],
        "play_pounce": [
            sn,
            _compose(pl0, dx=-5, motion="pounce"),
            _compose(pl1, dx=5, motion="pounce"),
            _compose(pl0, dx=3),
            _compose(pl1, dx=-2),
            sn,
        ],
        "paw_batting": [
            sn,
            _compose(gr0, dx=-3, motion="paw"),
            _compose(pl0, dx=2, motion="paw"),
            _compose(gr1, dx=1, motion="paw"),
            _compose(gr0, dx=-1),
            sn,
        ],
        "chase_loop": [
            sn,
            _compose(pl0, dx=-10, motion="chase"),
            _compose(pl1, dx=8, motion="chase"),
            _compose(pl0, dx=6, motion="chase"),
            _compose(pl1, dx=-8, motion="chase"),
            sn,
        ],
        "bunny_kick": [
            sn,
            _compose(pl1, dy=-1, motion="kick"),
            _compose(pl0, dy=2, motion="kick"),
            _compose(pl1, dy=1, motion="kick"),
            _compose(gr0, dy=1),
            sn,
        ],
        "standing_swat": [
            sn,
            _compose(gr1, dy=-6, sy=1.03),
            _compose(gr0, dy=-4, sy=1.02),
            _compose(pl0, dy=-2),
            _compose(gr1, dy=-3, motion="paw"),
            sn,
        ],
        "standoff": [
            sn,
            _compose(sn, dx=-5),
            _compose(sn, dx=5),
            _compose(gr0, dy=-1),
            _compose(sn, dx=0),
            sn,
        ],
        "explosive_clash": [
            sn,
            _compose(pl0, dx=-7, motion="clash"),
            _compose(pl1, dx=7, motion="clash"),
            _compose(gr1, motion="clash"),
            _compose(pl0, dx=-2, motion="clash"),
            sn,
        ],
        "ear_cleaning": [
            sn,
            _compose(gr1, dy=-1),
            _compose(gr0, dy=0),
            _compose(gr1, dy=1),
            _compose(sn_b, dy=0),
            sn,
        ],
        "face_wash_assist": [
            sn,
            _compose(gr0, dy=0),
            _compose(sn_b, dy=1),
            _compose(gr1, dy=0),
            _compose(sn, dy=0),
            sn,
        ],
    }


def generate() -> None:
    if not BASE_ATLAS.exists():
        raise FileNotFoundError(f"Missing base atlas: {BASE_ATLAS}")

    with Image.open(BASE_ATLAS) as atlas:
        atlas_rgba = atlas.convert("RGBA")
        cells = _extract_cells(atlas_rgba)

    named_cells = {
        "gr0": cells[0],
        "gr1": cells[1],
        "pl0": cells[2],
        "pl1": cells[3],
        "sn": cells[4],
        "sn_b": cells[5],
    }
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

