from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

from _duo_cat_pack import APP_STATIC_ROOT, ATLAS_H, ATLAS_W, CLIP_ORDER, FRAME_H, FRAME_W, PUBLIC_ROOT

CONTACT_SHEET_NAME = "__contact_sheet.png"
GRID_COLS = 4
PADDING = 12
LABEL_H = 24
BACKGROUND = (20, 20, 20, 255)
LABEL_COLOR = (245, 245, 245, 255)


def _first_cell(atlas_path: Path) -> Image.Image:
    if not atlas_path.exists():
        raise FileNotFoundError(f"Missing atlas: {atlas_path}")
    atlas = Image.open(atlas_path).convert("RGBA")
    try:
        if atlas.size != (ATLAS_W, ATLAS_H):
            raise ValueError(f"{atlas_path} must be {ATLAS_W}x{ATLAS_H}, got {atlas.size}")
        return atlas.crop((0, 0, FRAME_W, FRAME_H))
    finally:
        atlas.close()


def _build_for_root(root: Path) -> Path:
    atlas_root = root / "duo_cats"
    rows = int(math.ceil(float(len(CLIP_ORDER)) / float(GRID_COLS)))
    tile_w = FRAME_W
    tile_h = FRAME_H + LABEL_H
    out_w = (GRID_COLS * tile_w) + ((GRID_COLS + 1) * PADDING)
    out_h = (rows * tile_h) + ((rows + 1) * PADDING)
    out = Image.new("RGBA", (out_w, out_h), BACKGROUND)
    draw = ImageDraw.Draw(out)
    try:
        for idx, clip in enumerate(CLIP_ORDER):
            col = idx % GRID_COLS
            row = idx // GRID_COLS
            x = PADDING + (col * (tile_w + PADDING))
            y = PADDING + (row * (tile_h + PADDING))
            cell = _first_cell(atlas_root / f"{clip}_p0.png")
            try:
                out.paste(cell, (x, y), cell)
            finally:
                cell.close()
            draw.text((x + 8, y + FRAME_H + 4), clip, fill=LABEL_COLOR)
        out_path = atlas_root / CONTACT_SHEET_NAME
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out.save(out_path)
        return out_path
    finally:
        out.close()


def build() -> None:
    app_path = _build_for_root(APP_STATIC_ROOT)
    public_path = _build_for_root(PUBLIC_ROOT)
    print(f"wrote duo-cat contact sheets: {app_path} and {public_path}")


if __name__ == "__main__":
    build()
