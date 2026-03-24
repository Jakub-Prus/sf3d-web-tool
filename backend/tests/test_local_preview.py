from io import BytesIO
from pathlib import Path

from PIL import Image

from app.services.local_preview import LOCAL_PREVIEW_GRID_SIZE, generate_local_preview_mesh


def _create_opaque_subject_image() -> bytes:
    image = Image.new("RGBA", (12, 12), (40, 90, 220, 255))
    for x in range(3, 9):
        for y in range(2, 10):
            image.putpixel((x, y), (240, 190, 30, 255))

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_local_preview_mesh_reuses_opencv_mask_for_opaque_backgrounds(tmp_path: Path) -> None:
    result = generate_local_preview_mesh(
        processed_image_bytes=_create_opaque_subject_image(),
        artifact_dir=tmp_path,
    )

    assert result.mesh_path.is_file()
    assert result.occupied_cells > 0
    assert result.occupied_cells < LOCAL_PREVIEW_GRID_SIZE * LOCAL_PREVIEW_GRID_SIZE
    assert any("OpenCV" in note for note in result.notes)
