from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image, UnidentifiedImageError
from app.services.masking import detect_foreground_mask

PREPROCESS_CANVAS_SIZE_PX = 1024
RGBA_MODE = "RGBA"
PNG_SUFFIX = ".png"
LOCAL_BACKGROUND_REMOVAL_STEP = "Remove background with local border-connected color matting"


@dataclass(frozen=True)
class PreprocessOptions:
    remove_background: bool
    auto_crop: bool
    normalize_size: bool


@dataclass(frozen=True)
class PreprocessResult:
    processed_bytes: bytes
    output_suffix: str
    requested_steps: list[str]
    applied_steps: list[str]
    notes: list[str]
    metadata: dict[str, int | str | None]


class InvalidInputImageError(ValueError):
    pass


def build_preprocessing_steps(options: PreprocessOptions) -> list[str]:
    steps: list[str] = []

    if options.remove_background:
        steps.append("Remove background before inference")
    if options.auto_crop:
        steps.append("Auto-crop around the object silhouette")
    if options.normalize_size:
        steps.append("Normalize the image canvas size")
    if not steps:
        steps.append("Pass image through without preprocessing")

    return steps


def preprocess_image(image_bytes: bytes, options: PreprocessOptions) -> PreprocessResult:
    requested_steps = build_preprocessing_steps(options)
    applied_steps: list[str] = []
    notes: list[str] = []

    try:
        with Image.open(BytesIO(image_bytes)) as source_image:
            working_image = source_image.convert(RGBA_MODE)
            original_width, original_height = working_image.size

            if options.remove_background:
                working_image, background_removed, background_note = _remove_background(working_image)
                notes.append(background_note)
                if background_removed:
                    applied_steps.append(LOCAL_BACKGROUND_REMOVAL_STEP)

            alpha_bbox = _get_alpha_bbox(working_image)
            if options.auto_crop:
                if alpha_bbox is not None:
                    working_image = working_image.crop(alpha_bbox)
                    applied_steps.append("Auto-crop around the detected transparent silhouette")
                else:
                    notes.append(
                        "Auto-crop was requested, but no reliable alpha silhouette was available for cropping."
                    )

            if options.normalize_size:
                working_image = _normalize_to_square_canvas(working_image, PREPROCESS_CANVAS_SIZE_PX)
                applied_steps.append(f"Normalize the image canvas to {PREPROCESS_CANVAS_SIZE_PX}px square")

            processed_width, processed_height = working_image.size
            output_buffer = BytesIO()
            working_image.save(output_buffer, format="PNG")
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        raise InvalidInputImageError("Upload a valid PNG, JPEG, or WEBP image.") from exc

    return PreprocessResult(
        processed_bytes=output_buffer.getvalue(),
        output_suffix=PNG_SUFFIX,
        requested_steps=requested_steps,
        applied_steps=applied_steps,
        notes=notes,
        metadata={
            "original_width": original_width,
            "original_height": original_height,
            "processed_width": processed_width,
            "processed_height": processed_height,
            "canvas_size_px": PREPROCESS_CANVAS_SIZE_PX if options.normalize_size else None,
        },
    )


def _get_alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    alpha_channel = image.getchannel("A")
    extrema = alpha_channel.getextrema()
    if extrema == (255, 255):
        return None
    return alpha_channel.getbbox()


def _normalize_to_square_canvas(image: Image.Image, canvas_size: int) -> Image.Image:
    source_width, source_height = image.size
    max_dimension = max(source_width, source_height)
    if max_dimension == 0:
        return image

    scale = min(canvas_size / source_width, canvas_size / source_height)
    resized_width = max(1, round(source_width * scale))
    resized_height = max(1, round(source_height * scale))
    resized_image = image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)

    canvas = Image.new(RGBA_MODE, (canvas_size, canvas_size), (0, 0, 0, 0))
    offset = ((canvas_size - resized_width) // 2, (canvas_size - resized_height) // 2)
    canvas.paste(resized_image, offset)
    return canvas


def _remove_background(image: Image.Image) -> tuple[Image.Image, bool, str]:
    mask_result = detect_foreground_mask(image)
    if not mask_result.confident:
        return image, False, mask_result.note

    if mask_result.source == "alpha":
        return image, True, mask_result.note

    rgba_image = image.convert(RGBA_MODE)
    rgba_array = np.asarray(rgba_image, dtype=np.uint8).copy()
    rgba_array[~mask_result.foreground_mask, 3] = 0
    return Image.fromarray(rgba_array), True, mask_result.note
