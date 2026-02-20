from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image


def _load_generator_module():
    module_path = Path(__file__).resolve().parents[2] / "tools" / "build_duo_atlas_metadata.py"
    spec = importlib.util.spec_from_file_location("build_duo_atlas_metadata", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def test_write_metadata_has_expected_shape_and_valid_clips(tmp_path: Path) -> None:
    module = _load_generator_module()

    atlas = tmp_path / "cats_duo_atlas.png"
    Image.new("RGBA", (1536, 512), (0, 0, 0, 0)).save(atlas)
    output = tmp_path / "cats_duo_atlas.json"

    written_path = module.write_metadata(atlas, output)
    assert written_path == output
    assert written_path.exists()

    data = json.loads(written_path.read_text(encoding="utf-8"))
    assert data["imagePath"] == "/static/sprites/cats/cats_duo_atlas.png"
    assert data["frameW"] == 512
    assert data["frameH"] == 256
    assert data["cols"] == 3
    assert data["rows"] == 2

    frames = data["frames"]
    assert len(frames) == 6
    for index, frame in enumerate(frames):
        assert frame["id"] == index
        assert frame["w"] == 512
        assert frame["h"] == 256
        assert frame["x"] in {0, 512, 1024}
        assert frame["y"] in {0, 256}

    valid_ids = {frame["id"] for frame in frames}
    for clip in data["clips"].values():
        assert clip["fps"] > 0
        assert clip["loop"] is True
        assert clip["frames"]
        assert all(frame_id in valid_ids for frame_id in clip["frames"])


def test_invalid_dimensions_raise_value_error(tmp_path: Path) -> None:
    module = _load_generator_module()
    atlas = tmp_path / "bad_size.png"
    Image.new("RGBA", (1200, 512), (0, 0, 0, 0)).save(atlas)
    with pytest.raises(ValueError, match="atlas must be 1536x512"):
        module.build_metadata(atlas)
