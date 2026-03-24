from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np
from PIL import Image

RGBA_MODE = "RGBA"
RGB_CHANNEL_COUNT = 3
FULLY_OPAQUE_ALPHA = 255
ALPHA_FOREGROUND_THRESHOLD = 24
BORDER_SAMPLE_WIDTH_PX = 2
LAB_DISTANCE_BASE_THRESHOLD = 18.0
LAB_DISTANCE_NOISE_MULTIPLIER = 2.5
MORPH_KERNEL_MIN_SIZE = 3
MIN_FOREGROUND_PIXEL_RATIO = 0.01
MAX_FOREGROUND_PIXEL_RATIO = 0.99
MIN_COMPONENT_AREA_RATIO = 0.002

MaskSource = Literal["alpha", "opencv", "fallback"]


@dataclass(frozen=True)
class ForegroundMaskResult:
    foreground_mask: np.ndarray
    confident: bool
    source: MaskSource
    note: str


def detect_foreground_mask(image: Image.Image) -> ForegroundMaskResult:
    rgba_image = image.convert(RGBA_MODE)
    rgba_array = np.asarray(rgba_image, dtype=np.uint8)
    alpha_channel = rgba_array[..., 3]

    if np.any(alpha_channel < FULLY_OPAQUE_ALPHA):
        return ForegroundMaskResult(
            foreground_mask=alpha_channel >= ALPHA_FOREGROUND_THRESHOLD,
            confident=True,
            source="alpha",
            note="Background removal reused the existing transparent alpha channel in the image.",
        )

    rgb_array = rgba_array[..., :RGB_CHANNEL_COUNT]
    foreground_mask = _detect_foreground_mask_with_opencv(rgb_array)
    total_pixel_count = foreground_mask.size
    foreground_pixel_count = int(foreground_mask.sum())
    foreground_ratio = foreground_pixel_count / total_pixel_count if total_pixel_count else 0.0

    if foreground_ratio < MIN_FOREGROUND_PIXEL_RATIO or foreground_ratio > MAX_FOREGROUND_PIXEL_RATIO:
        fallback_mask = np.ones(foreground_mask.shape, dtype=bool)
        return ForegroundMaskResult(
            foreground_mask=fallback_mask,
            confident=False,
            source="fallback",
            note=(
                "Background removal could not confidently isolate a border-connected background region, "
                "so the original opaque image was preserved."
            ),
        )

    return ForegroundMaskResult(
        foreground_mask=foreground_mask,
        confident=True,
        source="opencv",
        note=(
            "Background removal used OpenCV border-connected color matting in Lab space and supports "
            "white plus other mostly solid-color backdrops."
        ),
    )


def _detect_foreground_mask_with_opencv(rgb_array: np.ndarray) -> np.ndarray:
    image_height, image_width = rgb_array.shape[:2]
    lab_image = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2LAB).astype(np.float32)
    border_mask = _build_border_mask(image_height, image_width)
    background_samples = lab_image[border_mask]
    background_color = np.median(background_samples, axis=0)
    background_sample_distances = np.linalg.norm(background_samples - background_color, axis=1)
    threshold = max(
        LAB_DISTANCE_BASE_THRESHOLD,
        float(np.percentile(background_sample_distances, 90)) * LAB_DISTANCE_NOISE_MULTIPLIER,
    )

    distance_from_background = np.linalg.norm(lab_image - background_color, axis=2)
    candidate_background = (distance_from_background <= threshold).astype(np.uint8)
    label_count, labels = cv2.connectedComponents(candidate_background, connectivity=4)
    if label_count <= 1:
        return np.ones((image_height, image_width), dtype=bool)

    border_labels = np.unique(
        np.concatenate(
            [
                labels[0, :],
                labels[-1, :],
                labels[:, 0],
                labels[:, -1],
            ]
        )
    )
    background_mask = np.isin(labels, border_labels) & (candidate_background > 0)
    foreground_mask = ~background_mask

    foreground_uint8 = foreground_mask.astype(np.uint8) * FULLY_OPAQUE_ALPHA
    kernel = np.ones((_compute_kernel_size(image_height, image_width),) * 2, dtype=np.uint8)
    foreground_uint8 = cv2.morphologyEx(foreground_uint8, cv2.MORPH_CLOSE, kernel)
    foreground_uint8 = cv2.morphologyEx(foreground_uint8, cv2.MORPH_OPEN, kernel)

    component_count, component_labels, component_stats, _ = cv2.connectedComponentsWithStats(
        (foreground_uint8 > 0).astype(np.uint8),
        connectivity=8,
    )
    if component_count <= 1:
        return foreground_uint8 > 0

    minimum_component_area = max(
        1,
        round(image_height * image_width * MIN_COMPONENT_AREA_RATIO),
    )
    refined_mask = np.zeros((image_height, image_width), dtype=bool)
    for component_index in range(1, component_count):
        component_area = int(component_stats[component_index, cv2.CC_STAT_AREA])
        if component_area >= minimum_component_area:
            refined_mask |= component_labels == component_index

    if np.any(refined_mask):
        return refined_mask

    return foreground_uint8 > 0


def _build_border_mask(image_height: int, image_width: int) -> np.ndarray:
    border_width = min(BORDER_SAMPLE_WIDTH_PX, image_height, image_width)
    border_mask = np.zeros((image_height, image_width), dtype=bool)
    border_mask[:border_width, :] = True
    border_mask[-border_width:, :] = True
    border_mask[:, :border_width] = True
    border_mask[:, -border_width:] = True
    return border_mask


def _compute_kernel_size(image_height: int, image_width: int) -> int:
    kernel_size = max(MORPH_KERNEL_MIN_SIZE, round(min(image_height, image_width) * 0.03))
    if kernel_size % 2 == 0:
        kernel_size += 1
    return kernel_size
