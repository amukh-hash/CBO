from __future__ import annotations

from pathlib import Path
from typing import Literal, Mapping, Sequence, TypedDict

CatName = Literal["calico", "gray"]

# Shared duo anchor (top-left) used by both cats and pair poses.
ANCHOR_X = 193
ANCHOR_Y = 92

POSE_ASSET_ROOT = Path("app/ui/static")


class CatDirective(TypedDict, total=False):
    pose: str
    dx: int
    dy: int
    flipX: bool


class OverlayDirective(TypedDict, total=False):
    name: str
    dx: int
    dy: int
    flipX: bool


class FrameDirective(TypedDict, total=False):
    calico: CatDirective
    gray: CatDirective
    pair_pose: str
    dx: int
    dy: int
    flipX: bool
    z_order: list[CatName]
    overlays: list[OverlayDirective]


CALICO_POSES: dict[str, Path] = {
    "calico_sit": POSE_ASSET_ROOT / "cat_pose_0_0.png",
    "calico_curl": POSE_ASSET_ROOT / "cat_pose_0_1.png",
    "calico_pounce": POSE_ASSET_ROOT / "cat_pose_0_2.png",
    "calico_groom": POSE_ASSET_ROOT / "cat_pose_0_3.png",
}

GRAY_POSES: dict[str, Path] = {
    "gray_loaf": POSE_ASSET_ROOT / "cat_pose_1_0.png",
    "gray_curl": POSE_ASSET_ROOT / "cat_pose_1_1.png",
    "gray_sit": POSE_ASSET_ROOT / "cat_pose_1_2.png",
    "gray_stand": POSE_ASSET_ROOT / "cat_pose_1_3.png",
}

PAIR_POSES: dict[str, Path] = {
    "snuggle_pair_base": POSE_ASSET_ROOT / "snuggling-cats.png",
    "snuggle_pair_breathe": POSE_ASSET_ROOT / "cat_pose_2_0.png",
    "snuggle_pair_twitch": POSE_ASSET_ROOT / "cat_pose_2_1.png",
    "snuggle_pair_tight": POSE_ASSET_ROOT / "cat_pose_2_2.png",
    "snuggle_pair_side": POSE_ASSET_ROOT / "cat_pose_2_3.png",
}

DEFAULT_Z_ORDER: tuple[CatName, CatName] = ("calico", "gray")
VALID_Z_ORDERS = {
    ("calico", "gray"),
    ("gray", "calico"),
}

INTERACTION_CLIPS = frozenset(
    {
        "nose_boop",
        "mutual_groom",
        "paw_batting",
        "play_pounce",
        "bunny_kick",
        "standing_swat",
        "explosive_clash",
    }
)
CONTACT_REQUIRED_CLIPS = frozenset(
    {
        "nose_boop",
        "mutual_groom",
        "paw_batting",
        "play_pounce",
        "bunny_kick",
        "standing_swat",
    }
)
NON_CONTACT_CLIPS = frozenset({"standoff"})
MIDDLE_FRAME_INDICES = (1, 2, 3, 4)

# Validation and rendering safety thresholds.
MIN_CAT_ALPHA = 2000
MIN_CONTACT_OVERLAP = 80
MAX_NON_CONTACT_OVERLAP = 60
MAX_OCCLUSION_RATIO = 0.95
MIN_VISIBLE_RATIO = 0.20


CALICO_SNUGGLE = {"pose": "calico_curl", "dx": 10, "dy": 2}
GRAY_SNUGGLE = {"pose": "gray_curl", "dx": -22, "dy": 2, "flipX": True}


def _cat(pose: str, *, dx: int = 0, dy: int = 0, flip_x: bool = False) -> CatDirective:
    frame: CatDirective = {"pose": pose, "dx": dx, "dy": dy}
    if flip_x:
        frame["flipX"] = True
    return frame


def _overlay(name: str, *, dx: int = 0, dy: int = 0, flip_x: bool = False) -> OverlayDirective:
    overlay: OverlayDirective = {"name": name, "dx": dx, "dy": dy}
    if flip_x:
        overlay["flipX"] = True
    return overlay


def _pair(
    pose: str,
    *,
    dx: int = 0,
    dy: int = 0,
    flip_x: bool = False,
    calico: CatDirective | None = None,
    gray: CatDirective | None = None,
    z_order: tuple[CatName, CatName] | None = None,
    overlays: list[OverlayDirective] | None = None,
) -> FrameDirective:
    frame: FrameDirective = {"pair_pose": pose, "dx": dx, "dy": dy}
    if flip_x:
        frame["flipX"] = True
    if calico:
        frame["calico"] = calico
    if gray:
        frame["gray"] = gray
    if z_order:
        frame["z_order"] = list(z_order)
    if overlays:
        frame["overlays"] = overlays
    return frame


def _cats(
    calico: CatDirective,
    gray: CatDirective,
    *,
    z_order: tuple[CatName, CatName] | None = None,
    overlays: list[OverlayDirective] | None = None,
) -> FrameDirective:
    frame: FrameDirective = {"calico": calico, "gray": gray}
    if z_order:
        frame["z_order"] = list(z_order)
    if overlays:
        frame["overlays"] = overlays
    return frame


def _seam_snuggle() -> FrameDirective:
    return _pair(
        "snuggle_pair_base",
        calico=CALICO_SNUGGLE.copy(),
        gray=GRAY_SNUGGLE.copy(),
        z_order=("gray", "calico"),
    )


def _snuggle_idle_middle_cycle() -> list[FrameDirective]:
    return [
        _pair(
            "snuggle_pair_breathe",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=3),
            gray=_cat("gray_curl", dx=-22, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_tight",
            dy=2,
            calico=_cat("calico_curl", dx=9, dy=4),
            gray=_cat("gray_curl", dx=-21, dy=4, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_twitch",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=2),
            gray=_cat("gray_curl", dx=-22, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("ear_twitch", dx=70, dy=2)],
        ),
        _pair(
            "snuggle_pair_tight",
            dy=3,
            calico=_cat("calico_curl", dx=9, dy=5),
            gray=_cat("gray_curl", dx=-21, dy=5, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=2,
            calico=_cat("calico_curl", dx=10, dy=4),
            gray=_cat("gray_curl", dx=-22, dy=4, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("tail_flick", dx=48, dy=12)],
        ),
        _pair(
            "snuggle_pair_side",
            dy=0,
            calico=_cat("calico_curl", dx=10, dy=2),
            gray=_cat("gray_curl", dx=-22, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("ear_twitch", dx=68, dy=1)],
        ),
        _pair(
            "snuggle_pair_tight",
            dy=2,
            calico=_cat("calico_curl", dx=9, dy=3),
            gray=_cat("gray_curl", dx=-21, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=3),
            gray=_cat("gray_curl", dx=-22, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_twitch",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=2),
            gray=_cat("gray_curl", dx=-22, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("tail_flick", dx=50, dy=11)],
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=0,
            calico=_cat("calico_curl", dx=10, dy=2),
            gray=_cat("gray_curl", dx=-22, dy=2, flip_x=True),
            z_order=("gray", "calico"),
        ),
    ]


def _build_snuggle_idle_script() -> list[FrameDirective]:
    middle = _snuggle_idle_middle_cycle()
    frames = [
        _seam_snuggle(),
        *middle,
        *middle,
        *middle[:2],
        _seam_snuggle(),
    ]
    return frames


def middle_frame_indices(total_frames: int) -> tuple[int, ...]:
    if total_frames <= 2:
        return ()
    return tuple(range(1, total_frames - 1))


POSE_SCRIPTS: dict[str, list[FrameDirective]] = {
    "snuggle_idle": _build_snuggle_idle_script(),
    "mutual_groom": [
        _seam_snuggle(),
        _cats(
            _cat("calico_groom", dx=22, dy=6),
            _cat("gray_loaf", dx=-32, dy=18, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_groom", dx=18, dy=6),
            _cat("gray_loaf", dx=-28, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("lick_left", dx=-2, dy=0)],
        ),
        _cats(
            _cat("calico_groom", dx=14, dy=5),
            _cat("gray_loaf", dx=-24, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("lick_left", dx=-3, dy=0)],
        ),
        _cats(
            _cat("calico_groom", dx=10, dy=5),
            _cat("gray_sit", dx=-18, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("lick_right", dx=0, dy=0)],
        ),
        _cats(
            _cat("calico_groom", dx=6, dy=5),
            _cat("gray_sit", dx=-12, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("lick_right", dx=2, dy=0)],
        ),
        _cats(
            _cat("calico_groom", dx=4, dy=5),
            _cat("gray_sit", dx=-10, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("lick_right", dx=3, dy=0)],
        ),
        _cats(
            _cat("calico_sit", dx=8, dy=8),
            _cat("gray_loaf", dx=-14, dy=18, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_sit", dx=12, dy=8),
            _cat("gray_loaf", dx=-18, dy=18, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_sit", dx=16, dy=8),
            _cat("gray_loaf", dx=-22, dy=18, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=3),
            gray=_cat("gray_curl", dx=-22, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _seam_snuggle(),
    ],
    "nose_boop": [
        _seam_snuggle(),
        _cats(
            _cat("calico_sit", dx=36, dy=8),
            _cat("gray_sit", dx=-36, dy=10, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_sit", dx=28, dy=8),
            _cat("gray_sit", dx=-28, dy=10, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_sit", dx=20, dy=8),
            _cat("gray_sit", dx=-20, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("boop_ping", dx=0, dy=-1)],
        ),
        _cats(
            _cat("calico_sit", dx=14, dy=8),
            _cat("gray_sit", dx=-14, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("boop_ping", dx=0, dy=-1)],
        ),
        _cats(
            _cat("calico_sit", dx=10, dy=8),
            _cat("gray_sit", dx=-10, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("boop_ping", dx=0, dy=-1)],
        ),
        _cats(
            _cat("calico_sit", dx=16, dy=8),
            _cat("gray_sit", dx=-16, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("boop_ping", dx=0, dy=-1)],
        ),
        _cats(
            _cat("calico_sit", dx=24, dy=8),
            _cat("gray_sit", dx=-24, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("tail_flick", dx=46, dy=12)],
        ),
        _cats(
            _cat("calico_sit", dx=30, dy=8),
            _cat("gray_sit", dx=-30, dy=10, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _seam_snuggle(),
    ],
    "snuggle_curl": [
        _seam_snuggle(),
        _pair(
            "snuggle_pair_breathe",
            dy=2,
            calico=_cat("calico_curl", dx=10, dy=4),
            gray=_cat("gray_curl", dx=-22, dy=4, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_tight",
            dy=3,
            calico=_cat("calico_curl", dx=9, dy=4),
            gray=_cat("gray_curl", dx=-21, dy=4, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_tight",
            dy=4,
            calico=_cat("calico_curl", dx=9, dy=5),
            gray=_cat("gray_curl", dx=-21, dy=5, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("curl_swish", dx=56, dy=24)],
        ),
        _pair(
            "snuggle_pair_tight",
            dy=5,
            calico=_cat("calico_curl", dx=8, dy=6),
            gray=_cat("gray_curl", dx=-20, dy=6, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("curl_swish", dx=58, dy=26)],
        ),
        _pair(
            "snuggle_pair_tight",
            dy=2,
            calico=_cat("calico_curl", dx=9, dy=5),
            gray=_cat("gray_curl", dx=-21, dy=5, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("curl_swish", dx=56, dy=24)],
        ),
        _pair(
            "snuggle_pair_tight",
            dy=3,
            calico=_cat("calico_curl", dx=9, dy=4),
            gray=_cat("gray_curl", dx=-21, dy=4, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=2,
            calico=_cat("calico_curl", dx=10, dy=4),
            gray=_cat("gray_curl", dx=-22, dy=4, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=3),
            gray=_cat("gray_curl", dx=-22, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _seam_snuggle(),
    ],
    "play_pounce": [
        _seam_snuggle(),
        _cats(
            _cat("calico_pounce", dx=52, dy=20),
            _cat("gray_sit", dx=-44, dy=10, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_pounce", dx=44, dy=20),
            _cat("gray_sit", dx=-38, dy=10, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_pounce", dx=34, dy=18),
            _cat("gray_sit", dx=-30, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("pounce_trail", dx=10, dy=16)],
        ),
        _cats(
            _cat("calico_pounce", dx=24, dy=16),
            _cat("gray_sit", dx=-24, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("pounce_trail", dx=8, dy=14)],
        ),
        _cats(
            _cat("calico_pounce", dx=14, dy=15),
            _cat("gray_loaf", dx=-16, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("impact_star", dx=4, dy=10)],
        ),
        _cats(
            _cat("calico_pounce", dx=6, dy=14),
            _cat("gray_loaf", dx=-10, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("impact_star", dx=2, dy=8)],
        ),
        _cats(
            _cat("calico_curl", dx=8, dy=16),
            _cat("gray_loaf", dx=-14, dy=18, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_curl", dx=10, dy=17),
            _cat("gray_loaf", dx=-18, dy=18, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_curl", dx=12, dy=18),
            _cat("gray_loaf", dx=-22, dy=18, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=3),
            gray=_cat("gray_curl", dx=-22, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _seam_snuggle(),
    ],
    "paw_batting": [
        _seam_snuggle(),
        _cats(
            _cat("calico_sit", dx=32, dy=8),
            _cat("gray_sit", dx=-32, dy=10, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_sit", dx=26, dy=8),
            _cat("gray_sit", dx=-26, dy=10, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_groom", dx=18, dy=7),
            _cat("gray_sit", dx=-22, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("paw_contact", dx=0, dy=8)],
        ),
        _cats(
            _cat("calico_groom", dx=12, dy=6),
            _cat("gray_sit", dx=-18, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("paw_contact", dx=2, dy=8)],
        ),
        _cats(
            _cat("calico_groom", dx=8, dy=6),
            _cat("gray_stand", dx=-12, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("paw_contact", dx=3, dy=6)],
        ),
        _cats(
            _cat("calico_sit", dx=12, dy=8),
            _cat("gray_stand", dx=-8, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("paw_contact", dx=4, dy=6, flip_x=True)],
        ),
        _cats(
            _cat("calico_sit", dx=16, dy=8),
            _cat("gray_stand", dx=-12, dy=2, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_sit", dx=20, dy=8),
            _cat("gray_sit", dx=-22, dy=10, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_sit", dx=24, dy=8),
            _cat("gray_sit", dx=-24, dy=10, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=3),
            gray=_cat("gray_curl", dx=-22, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _seam_snuggle(),
    ],
    "chase_loop": [
        _cats(
            _cat("calico_pounce", dx=18, dy=14),
            _cat("gray_stand", dx=-24, dy=2, flip_x=True),
            overlays=[_overlay("chase_arc", dx=-6, dy=10)],
        ),
        _cats(
            _cat("calico_pounce", dx=4, dy=14),
            _cat("gray_stand", dx=-10, dy=2, flip_x=True),
            overlays=[_overlay("chase_arc", dx=-3, dy=9)],
        ),
        _cats(
            _cat("calico_pounce", dx=-14, dy=14, flip_x=True),
            _cat("gray_stand", dx=10, dy=2),
            overlays=[_overlay("chase_arc", dx=-2, dy=8, flip_x=True)],
        ),
        _cats(
            _cat("calico_pounce", dx=-28, dy=14, flip_x=True),
            _cat("gray_stand", dx=24, dy=2),
            overlays=[_overlay("chase_arc", dx=0, dy=8, flip_x=True)],
        ),
        _cats(
            _cat("calico_pounce", dx=-8, dy=14, flip_x=True),
            _cat("gray_stand", dx=6, dy=2),
            overlays=[_overlay("chase_arc", dx=-1, dy=8, flip_x=True)],
        ),
        _cats(
            _cat("calico_pounce", dx=10, dy=14),
            _cat("gray_stand", dx=-12, dy=2, flip_x=True),
            overlays=[_overlay("chase_arc", dx=0, dy=8)],
        ),
        _cats(
            _cat("calico_pounce", dx=28, dy=14),
            _cat("gray_stand", dx=-30, dy=2, flip_x=True),
            overlays=[_overlay("chase_arc", dx=3, dy=8)],
        ),
        _cats(
            _cat("calico_pounce", dx=14, dy=14),
            _cat("gray_stand", dx=-16, dy=2, flip_x=True),
            overlays=[_overlay("chase_arc", dx=2, dy=8)],
        ),
        _cats(
            _cat("calico_pounce", dx=-2, dy=14, flip_x=True),
            _cat("gray_stand", dx=2, dy=2),
            overlays=[_overlay("chase_arc", dx=0, dy=8, flip_x=True)],
        ),
        _cats(
            _cat("calico_pounce", dx=-20, dy=14, flip_x=True),
            _cat("gray_stand", dx=18, dy=2),
            overlays=[_overlay("chase_arc", dx=1, dy=8, flip_x=True)],
        ),
        _cats(
            _cat("calico_pounce", dx=-4, dy=14, flip_x=True),
            _cat("gray_stand", dx=4, dy=2),
            overlays=[_overlay("chase_arc", dx=0, dy=8, flip_x=True)],
        ),
        _cats(
            _cat("calico_pounce", dx=18, dy=14),
            _cat("gray_stand", dx=-24, dy=2, flip_x=True),
            overlays=[_overlay("chase_arc", dx=-6, dy=10)],
        ),
    ],
    "bunny_kick": [
        _seam_snuggle(),
        _cats(
            _cat("calico_pounce", dx=8, dy=16),
            _cat("gray_loaf", dx=-18, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("kick_blur", dx=10, dy=18)],
        ),
        _cats(
            _cat("calico_pounce", dx=4, dy=16),
            _cat("gray_loaf", dx=-14, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("kick_blur", dx=9, dy=19)],
        ),
        _cats(
            _cat("calico_pounce", dx=0, dy=15),
            _cat("gray_loaf", dx=-10, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("kick_blur", dx=8, dy=20)],
        ),
        _cats(
            _cat("calico_pounce", dx=-4, dy=15),
            _cat("gray_loaf", dx=-8, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("kick_blur", dx=7, dy=20)],
        ),
        _cats(
            _cat("calico_groom", dx=0, dy=10),
            _cat("gray_loaf", dx=-10, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("kick_blur", dx=4, dy=16)],
        ),
        _cats(
            _cat("calico_groom", dx=4, dy=8),
            _cat("gray_loaf", dx=-12, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("kick_blur", dx=2, dy=16)],
        ),
        _cats(
            _cat("calico_pounce", dx=2, dy=14),
            _cat("gray_loaf", dx=-10, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("kick_blur", dx=5, dy=19)],
        ),
        _cats(
            _cat("calico_pounce", dx=-1, dy=14),
            _cat("gray_loaf", dx=-12, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("kick_blur", dx=6, dy=20)],
        ),
        _cats(
            _cat("calico_curl", dx=6, dy=14),
            _cat("gray_loaf", dx=-16, dy=18, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_curl", dx=8, dy=14),
            _cat("gray_loaf", dx=-18, dy=18, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_curl", dx=10, dy=15),
            _cat("gray_loaf", dx=-20, dy=18, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=3),
            gray=_cat("gray_curl", dx=-22, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _seam_snuggle(),
    ],
    "standing_swat": [
        _seam_snuggle(),
        _cats(
            _cat("calico_sit", dx=30, dy=8),
            _cat("gray_stand", dx=-30, dy=2, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_sit", dx=24, dy=8),
            _cat("gray_stand", dx=-24, dy=2, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_groom", dx=16, dy=6),
            _cat("gray_stand", dx=-18, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("paw_contact", dx=0, dy=4)],
        ),
        _cats(
            _cat("calico_groom", dx=10, dy=6),
            _cat("gray_stand", dx=-14, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("paw_contact", dx=1, dy=4)],
        ),
        _cats(
            _cat("calico_groom", dx=8, dy=6),
            _cat("gray_stand", dx=-12, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("paw_contact", dx=2, dy=5)],
        ),
        _cats(
            _cat("calico_sit", dx=12, dy=8),
            _cat("gray_stand", dx=-10, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("paw_contact", dx=2, dy=6, flip_x=True)],
        ),
        _cats(
            _cat("calico_sit", dx=16, dy=8),
            _cat("gray_stand", dx=-14, dy=2, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_sit", dx=20, dy=8),
            _cat("gray_stand", dx=-18, dy=2, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_sit", dx=24, dy=8),
            _cat("gray_stand", dx=-20, dy=2, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=3),
            gray=_cat("gray_curl", dx=-22, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _seam_snuggle(),
    ],
    "standoff": [
        _seam_snuggle(),
        _cats(
            _cat("calico_sit", dx=74, dy=8),
            _cat("gray_stand", dx=-74, dy=2, flip_x=True),
        ),
        _cats(
            _cat("calico_sit", dx=72, dy=8),
            _cat("gray_stand", dx=-72, dy=2, flip_x=True),
        ),
        _cats(
            _cat("calico_sit", dx=70, dy=8),
            _cat("gray_stand", dx=-70, dy=2, flip_x=True),
        ),
        _cats(
            _cat("calico_sit", dx=68, dy=8),
            _cat("gray_stand", dx=-68, dy=2, flip_x=True),
        ),
        _cats(
            _cat("calico_sit", dx=66, dy=8),
            _cat("gray_stand", dx=-66, dy=2, flip_x=True),
        ),
        _cats(
            _cat("calico_sit", dx=68, dy=8),
            _cat("gray_stand", dx=-68, dy=2, flip_x=True),
        ),
        _cats(
            _cat("calico_sit", dx=70, dy=8),
            _cat("gray_stand", dx=-70, dy=2, flip_x=True),
        ),
        _cats(
            _cat("calico_sit", dx=72, dy=8),
            _cat("gray_stand", dx=-72, dy=2, flip_x=True),
        ),
        _seam_snuggle(),
    ],
    "explosive_clash": [
        _seam_snuggle(),
        _cats(
            _cat("calico_pounce", dx=22, dy=14),
            _cat("gray_stand", dx=-26, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("clash_burst", dx=0, dy=6)],
        ),
        _cats(
            _cat("calico_pounce", dx=16, dy=13),
            _cat("gray_stand", dx=-20, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("clash_burst", dx=0, dy=4)],
        ),
        _cats(
            _cat("calico_pounce", dx=10, dy=12),
            _cat("gray_stand", dx=-14, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("clash_burst", dx=-1, dy=4)],
        ),
        _cats(
            _cat("calico_pounce", dx=6, dy=12),
            _cat("gray_stand", dx=-10, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("clash_burst", dx=-1, dy=4)],
        ),
        _cats(
            _cat("calico_pounce", dx=2, dy=12),
            _cat("gray_stand", dx=-6, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("clash_burst", dx=-2, dy=4)],
        ),
        _pair(
            "snuggle_pair_side",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=2),
            gray=_cat("gray_curl", dx=-22, dy=2, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=3),
            gray=_cat("gray_curl", dx=-22, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=0,
            calico=_cat("calico_curl", dx=10, dy=2),
            gray=_cat("gray_curl", dx=-22, dy=2, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("tail_flick", dx=48, dy=12)],
        ),
        _seam_snuggle(),
    ],
    "ear_cleaning": [
        _seam_snuggle(),
        _cats(
            _cat("calico_groom", dx=14, dy=6),
            _cat("gray_loaf", dx=-20, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("lick_left", dx=-4, dy=-2)],
        ),
        _cats(
            _cat("calico_groom", dx=12, dy=6),
            _cat("gray_loaf", dx=-18, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("lick_left", dx=-5, dy=-2)],
        ),
        _cats(
            _cat("calico_groom", dx=8, dy=5),
            _cat("gray_loaf", dx=-14, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("lick_left", dx=-6, dy=-2)],
        ),
        _cats(
            _cat("calico_groom", dx=6, dy=5),
            _cat("gray_loaf", dx=-12, dy=18, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("lick_left", dx=-6, dy=-2)],
        ),
        _cats(
            _cat("calico_sit", dx=10, dy=8),
            _cat("gray_loaf", dx=-14, dy=18, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_sit", dx=14, dy=8),
            _cat("gray_loaf", dx=-18, dy=18, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=3),
            gray=_cat("gray_curl", dx=-22, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_tight",
            dy=2,
            calico=_cat("calico_curl", dx=9, dy=3),
            gray=_cat("gray_curl", dx=-21, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _seam_snuggle(),
    ],
    "face_wash_assist": [
        _seam_snuggle(),
        _cats(
            _cat("calico_groom", dx=14, dy=6),
            _cat("gray_sit", dx=-22, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("paw_contact", dx=2, dy=4)],
        ),
        _cats(
            _cat("calico_groom", dx=12, dy=6),
            _cat("gray_sit", dx=-20, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("paw_contact", dx=1, dy=4)],
        ),
        _cats(
            _cat("calico_groom", dx=8, dy=5),
            _cat("gray_sit", dx=-16, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("paw_contact", dx=0, dy=4)],
        ),
        _cats(
            _cat("calico_groom", dx=6, dy=5),
            _cat("gray_sit", dx=-14, dy=10, flip_x=True),
            z_order=("gray", "calico"),
            overlays=[_overlay("paw_contact", dx=0, dy=4)],
        ),
        _cats(
            _cat("calico_sit", dx=12, dy=8),
            _cat("gray_sit", dx=-16, dy=10, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _cats(
            _cat("calico_sit", dx=16, dy=8),
            _cat("gray_sit", dx=-18, dy=10, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_breathe",
            dy=1,
            calico=_cat("calico_curl", dx=10, dy=3),
            gray=_cat("gray_curl", dx=-22, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _pair(
            "snuggle_pair_tight",
            dy=2,
            calico=_cat("calico_curl", dx=9, dy=3),
            gray=_cat("gray_curl", dx=-21, dy=3, flip_x=True),
            z_order=("gray", "calico"),
        ),
        _seam_snuggle(),
    ],
}


def resolve_pose(cat: CatName, key: str) -> Path:
    pose_map = CALICO_POSES if cat == "calico" else GRAY_POSES
    if key not in pose_map:
        raise KeyError(f"Unknown {cat} pose key '{key}'")
    path = pose_map[key]
    if not path.exists():
        raise FileNotFoundError(f"Missing {cat} pose image for key '{key}': {path}")
    return path


def resolve_pair_pose(key: str) -> Path:
    if key not in PAIR_POSES:
        raise KeyError(f"Unknown pair pose key '{key}'")
    path = PAIR_POSES[key]
    if not path.exists():
        raise FileNotFoundError(f"Missing pair pose image for key '{key}': {path}")
    return path


def _cat_dx(frame: FrameDirective, cat: CatName) -> int:
    cat_frame = frame.get(cat)
    if not isinstance(cat_frame, dict):
        return 0
    return int(cat_frame.get("dx", 0))


def _cat_pose_key(frame: FrameDirective, cat: CatName) -> str:
    cat_frame = frame.get(cat)
    if not isinstance(cat_frame, dict):
        return ""
    pose = cat_frame.get("pose")
    if not isinstance(pose, str):
        return ""
    return pose


def _validate_interaction_asymmetry(clip: str, frames: list[FrameDirective]) -> None:
    if clip not in INTERACTION_CLIPS:
        return
    has_asymmetric_middle_frame = False
    for frame_idx in middle_frame_indices(len(frames)):
        frame = frames[frame_idx]
        if "pair_pose" in frame:
            has_asymmetric_middle_frame = True
            break
        cal_pose = _cat_pose_key(frame, "calico")
        gray_pose = _cat_pose_key(frame, "gray")
        cal_dx = _cat_dx(frame, "calico")
        gray_dx = _cat_dx(frame, "gray")
        if cal_pose and gray_pose and (cal_pose != gray_pose):
            has_asymmetric_middle_frame = True
            break
        if cal_dx * gray_dx < 0:
            has_asymmetric_middle_frame = True
            break
    if not has_asymmetric_middle_frame:
        raise ValueError(
            f"{clip} is effectively symmetric in middle frames. "
            "Add different poses, opposite dx, or a pair_pose contact frame."
        )


def _validate_canonical_approach(clip: str, frames: list[FrameDirective]) -> None:
    if clip not in {"nose_boop", "mutual_groom"}:
        return
    if len(frames) < 5:
        raise ValueError(f"{clip} must contain at least 5 frames for approach validation")
    for idx in (1, 2):
        cal_dx = _cat_dx(frames[idx], "calico")
        gray_dx = _cat_dx(frames[idx], "gray")
        if cal_dx <= 0 or gray_dx >= 0:
            raise ValueError(
                f"{clip} frame_{idx} must approach: expected calico dx>0 and gray dx<0 (got {cal_dx}, {gray_dx})"
            )

    middle_dists: list[tuple[int, int]] = []
    for idx in range(1, len(frames) - 1):
        middle_dists.append((abs(_cat_dx(frames[idx], "calico")), abs(_cat_dx(frames[idx], "gray"))))

    if not middle_dists:
        return

    closest_idx = min(range(len(middle_dists)), key=lambda idx: middle_dists[idx][0] + middle_dists[idx][1])
    closest_cal, closest_gray = middle_dists[closest_idx]
    relax_found = False
    for idx in range(closest_idx + 1, len(middle_dists)):
        cal_dist, gray_dist = middle_dists[idx]
        if cal_dist >= closest_cal and gray_dist >= closest_gray:
            relax_found = True
            break

    if not relax_found:
        raise ValueError(f"{clip} never relaxes outward after closest-contact approach frame")


def validate_pose_scripts(clip_order: Sequence[str], clip_frame_counts: Mapping[str, int] | None = None) -> None:
    missing_clips = [clip for clip in clip_order if clip not in POSE_SCRIPTS]
    extra_clips = [clip for clip in POSE_SCRIPTS if clip not in clip_order]
    if missing_clips:
        raise ValueError(f"Pose scripts missing clip(s): {', '.join(missing_clips)}")
    if extra_clips:
        raise ValueError(f"Pose scripts include unknown clip(s): {', '.join(extra_clips)}")

    for clip in clip_order:
        frames = POSE_SCRIPTS[clip]
        expected = clip_frame_counts.get(clip) if clip_frame_counts is not None else None
        if expected is not None and len(frames) != expected:
            raise ValueError(f"{clip} must have exactly {expected} frame directives, got {len(frames)}")
        if len(frames) < 2:
            raise ValueError(f"{clip} must include at least 2 frame directives")

        for frame_idx, frame in enumerate(frames):
            has_pair_pose = "pair_pose" in frame
            has_both_cats = ("calico" in frame) and ("gray" in frame)
            if not has_pair_pose and not has_both_cats:
                raise ValueError(
                    f"{clip} frame_{frame_idx} must define pair_pose or both calico+gray directives"
                )

            if clip in INTERACTION_CLIPS and not has_both_cats:
                raise ValueError(
                    f"{clip} frame_{frame_idx} must define both calico and gray directives for interaction validation"
                )

            for cat in ("calico", "gray"):
                cat_frame = frame.get(cat)
                if not isinstance(cat_frame, dict):
                    continue
                pose = cat_frame.get("pose")
                if not isinstance(pose, str) or not pose:
                    raise ValueError(f"{clip} frame_{frame_idx} {cat} directive missing pose")
                resolve_pose(cat, pose)

            if has_pair_pose:
                pair_pose = frame.get("pair_pose")
                if not isinstance(pair_pose, str) or not pair_pose:
                    raise ValueError(f"{clip} frame_{frame_idx} pair_pose must be a non-empty string")
                resolve_pair_pose(pair_pose)

            z_order = frame.get("z_order")
            if z_order is not None:
                if not isinstance(z_order, list) or tuple(z_order) not in VALID_Z_ORDERS:
                    raise ValueError(
                        f"{clip} frame_{frame_idx} has invalid z_order={z_order}; expected one of {sorted(VALID_Z_ORDERS)}"
                    )

        _validate_interaction_asymmetry(clip, frames)
        _validate_canonical_approach(clip, frames)
