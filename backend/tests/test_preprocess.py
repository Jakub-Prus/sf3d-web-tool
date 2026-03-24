from io import BytesIO

import pytest
from PIL import Image

from app.services.preprocess import PREPROCESS_CANVAS_SIZE_PX, PreprocessOptions, preprocess_image


def create_test_image() -> bytes:
    image = Image.new("RGBA", (10, 6), (255, 0, 0, 255))
    for x in range(3):
        image.putpixel((x, 0), (0, 0, 0, 0))

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_preprocess_image_reports_applied_and_skipped_steps() -> None:
    result = preprocess_image(
        create_test_image(),
        PreprocessOptions(remove_background=True, auto_crop=True, normalize_size=True),
    )

    assert result.output_suffix == ".png"
    assert any("Remove background" in step for step in result.applied_steps)
    assert any("Auto-crop" in step for step in result.applied_steps)
    assert any("Normalize" in step for step in result.applied_steps)
    assert any("Background removal" in note for note in result.notes)
    assert result.metadata["original_width"] == 10
    assert result.metadata["processed_width"] == PREPROCESS_CANVAS_SIZE_PX


@pytest.mark.parametrize(
    ("background_rgba", "foreground_rgba"),
    [
        ((255, 255, 255, 255), (220, 30, 30, 255)),
        ((245, 245, 232, 255), (40, 150, 230, 255)),
        ((40, 90, 220, 255), (240, 190, 30, 255)),
        ((32, 32, 32, 255), (80, 240, 200, 255)),
    ],
)
def test_preprocess_image_removes_multiple_opaque_background_colors(
    background_rgba: tuple[int, int, int, int],
    foreground_rgba: tuple[int, int, int, int],
) -> None:
    image = Image.new("RGBA", (14, 10), background_rgba)
    for x in range(4, 10):
        for y in range(2, 8):
            image.putpixel((x, y), foreground_rgba)

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    result = preprocess_image(
        buffer.getvalue(),
        PreprocessOptions(remove_background=True, auto_crop=False, normalize_size=False),
    )
    processed_image = Image.open(BytesIO(result.processed_bytes)).convert("RGBA")

    assert any("Remove background" in step for step in result.applied_steps)
    assert any("OpenCV" in note for note in result.notes)
    assert processed_image.getpixel((0, 0))[3] == 0
    assert processed_image.getpixel((6, 5))[3] == 255


def test_preprocess_image_removes_white_background_and_crops_subject() -> None:
    image = Image.new("RGBA", (12, 12), (255, 255, 255, 255))
    for x in range(3, 9):
        for y in range(2, 10):
            image.putpixel((x, y), (220, 30, 30, 255))

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    result = preprocess_image(
        buffer.getvalue(),
        PreprocessOptions(remove_background=True, auto_crop=True, normalize_size=False),
    )
    processed_image = Image.open(BytesIO(result.processed_bytes)).convert("RGBA")

    assert any("Remove background" in step for step in result.applied_steps)
    assert any("Auto-crop" in step for step in result.applied_steps)
    assert processed_image.size == (6, 8)
    assert processed_image.getpixel((0, 0))[3] == 255


def test_preprocess_image_skips_crop_without_alpha_silhouette() -> None:
    image = Image.new("RGBA", (6, 6), (255, 0, 0, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    result = preprocess_image(
        buffer.getvalue(),
        PreprocessOptions(remove_background=False, auto_crop=True, normalize_size=False),
    )

    assert result.applied_steps == []
    assert any("Auto-crop was requested" in note for note in result.notes)
