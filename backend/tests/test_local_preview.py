from io import BytesIO
from pathlib import Path

from PIL import Image
import trimesh

from app.services.local_preview import LOCAL_PREVIEW_GRID_SIZE, generate_local_preview_mesh


def _image_to_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _create_opaque_subject_image() -> bytes:
    image = Image.new("RGBA", (12, 12), (40, 90, 220, 255))
    for x in range(3, 9):
        for y in range(2, 10):
            image.putpixel((x, y), (240, 190, 30, 255))
    return _image_to_bytes(image)


def _create_transparent_subject_image() -> bytes:
    image = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
    for x in range(3, 9):
        for y in range(2, 10):
            image.putpixel((x, y), (220, 30, 30, 255))
    return _image_to_bytes(image)


def _create_full_canvas_fallback_image() -> bytes:
    image = Image.new("RGBA", (12, 12), (255, 0, 0, 255))
    return _image_to_bytes(image)


def _load_preview_scene(mesh_path: Path) -> trimesh.Scene:
    return trimesh.load(mesh_path, force="scene")


def test_local_preview_mesh_reuses_opencv_mask_for_opaque_backgrounds(tmp_path: Path) -> None:
    result = generate_local_preview_mesh(
        processed_image_bytes=_create_opaque_subject_image(),
        artifact_dir=tmp_path,
    )
    mesh_scene = _load_preview_scene(result.mesh_path)
    geometries = list(mesh_scene.geometry.values())

    assert result.mesh_path.is_file()
    assert result.occupied_cells > 0
    assert result.occupied_cells < LOCAL_PREVIEW_GRID_SIZE * LOCAL_PREVIEW_GRID_SIZE
    assert any("OpenCV" in note for note in result.notes)
    assert len(geometries) == 1
    assert sum(len(geometry.vertices) for geometry in geometries) > 0
    assert sum(len(geometry.faces) for geometry in geometries) > 0


def test_local_preview_mesh_supports_transparent_inputs(tmp_path: Path) -> None:
    result = generate_local_preview_mesh(
        processed_image_bytes=_create_transparent_subject_image(),
        artifact_dir=tmp_path,
    )
    mesh_scene = _load_preview_scene(result.mesh_path)
    geometries = list(mesh_scene.geometry.values())

    assert result.mesh_path.is_file()
    assert result.occupied_cells > 0
    assert result.occupied_cells < LOCAL_PREVIEW_GRID_SIZE * LOCAL_PREVIEW_GRID_SIZE
    assert any("alpha channel" in note.lower() for note in result.notes)
    assert len(geometries) == 1
    assert sum(len(geometry.vertices) for geometry in geometries) > 0
    assert sum(len(geometry.faces) for geometry in geometries) > 0


def test_local_preview_mesh_falls_back_to_full_canvas_when_segmentation_fails(tmp_path: Path) -> None:
    result = generate_local_preview_mesh(
        processed_image_bytes=_create_full_canvas_fallback_image(),
        artifact_dir=tmp_path,
    )
    mesh_scene = _load_preview_scene(result.mesh_path)
    geometries = list(mesh_scene.geometry.values())

    assert result.mesh_path.is_file()
    assert result.occupied_cells == LOCAL_PREVIEW_GRID_SIZE * LOCAL_PREVIEW_GRID_SIZE
    assert any("full image canvas was extruded" in note for note in result.notes)
    assert len(geometries) == 1
    assert sum(len(geometry.vertices) for geometry in geometries) > 0
    assert sum(len(geometry.faces) for geometry in geometries) > 0
