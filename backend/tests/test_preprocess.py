from io import BytesIO

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
    assert any("Auto-crop" in step for step in result.applied_steps)
    assert any("Normalize" in step for step in result.applied_steps)
    assert any("Background removal was requested" in note for note in result.notes)
    assert result.metadata["original_width"] == 10
    assert result.metadata["processed_width"] == PREPROCESS_CANVAS_SIZE_PX


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
