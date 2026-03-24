from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image
from app.services.masking import detect_foreground_mask

LOCAL_PREVIEW_GRID_SIZE = 32
LOCAL_PREVIEW_BASE_DEPTH = 0.12
LOCAL_PREVIEW_DEPTH_VARIATION = 0.18
LOCAL_PREVIEW_MESH_NAME = "mesh.glb"
LOCAL_PREVIEW_MIN_OCCUPIED_CELLS = 1
RGB_MAX_VALUE = 255.0
LUMINANCE_WEIGHTS = np.asarray([0.299, 0.587, 0.114], dtype=np.float32)


@dataclass(frozen=True)
class LocalPreviewGenerationResult:
    mesh_path: Path
    notes: list[str]
    occupied_cells: int


def generate_local_preview_mesh(
    *,
    processed_image_bytes: bytes,
    artifact_dir: Path,
) -> LocalPreviewGenerationResult:
    with Image.open(BytesIO(processed_image_bytes)) as source_image:
        rgba_image = source_image.convert("RGBA")

    preview_image = _resize_for_preview(rgba_image, LOCAL_PREVIEW_GRID_SIZE)
    rgba_array = np.asarray(preview_image, dtype=np.uint8)
    occupancy_mask, segmentation_note = _build_occupancy_mask(rgba_array)

    occupied_cell_count = int(occupancy_mask.sum())
    if occupied_cell_count < LOCAL_PREVIEW_MIN_OCCUPIED_CELLS:
        occupancy_mask = np.ones(occupancy_mask.shape, dtype=bool)
        occupied_cell_count = int(occupancy_mask.sum())
        segmentation_note = (
            "Local preview fallback could not isolate the foreground, so the full image canvas was extruded."
        )

    mesh = _build_voxel_mesh(rgba_array, occupancy_mask)
    mesh_path = artifact_dir / LOCAL_PREVIEW_MESH_NAME
    mesh.export(mesh_path)

    return LocalPreviewGenerationResult(
        mesh_path=mesh_path,
        occupied_cells=occupied_cell_count,
        notes=[
            "Local preview mode generated a deterministic silhouette extrusion because the official SF3D runner is unavailable.",
            segmentation_note,
            (
                f"Local preview mesh grid size: {preview_image.size[0]}x{preview_image.size[1]} "
                f"with {occupied_cell_count} occupied cells."
            ),
        ],
    )


def _resize_for_preview(image: Image.Image, grid_size: int) -> Image.Image:
    source_width, source_height = image.size
    longest_edge = max(source_width, source_height, 1)
    scale = min(grid_size / source_width, grid_size / source_height)
    resized_width = max(1, round(source_width * scale))
    resized_height = max(1, round(source_height * scale))
    return image.resize((resized_width, resized_height), Image.Resampling.BOX)


def _build_occupancy_mask(rgba_array: np.ndarray) -> tuple[np.ndarray, str]:
    mask_result = detect_foreground_mask(Image.fromarray(rgba_array))
    return mask_result.foreground_mask, mask_result.note


def _build_voxel_mesh(rgba_array: np.ndarray, occupancy_mask: np.ndarray) -> trimesh.Trimesh:
    image_height, image_width = occupancy_mask.shape
    cell_width = 1.0 / image_width
    cell_height = 1.0 / image_height
    mesh_parts: list[trimesh.Trimesh] = []

    for row_index in range(image_height):
        for column_index in range(image_width):
            if not occupancy_mask[row_index, column_index]:
                continue

            rgba = rgba_array[row_index, column_index]
            extrusion_depth = _compute_extrusion_depth(rgba)
            box_mesh = trimesh.creation.box(extents=(cell_width, cell_height, extrusion_depth))
            box_mesh.apply_translation(
                (
                    (column_index + 0.5) * cell_width - 0.5,
                    0.5 - (row_index + 0.5) * cell_height,
                    0.0,
                )
            )
            mesh_parts.append(box_mesh)

    if not mesh_parts:
        raise ValueError("Local preview mesh generation expected at least one occupied cell.")

    combined_mesh = trimesh.util.concatenate(mesh_parts)
    combined_mesh.remove_unreferenced_vertices()
    return combined_mesh


def _compute_extrusion_depth(rgba: np.ndarray) -> float:
    rgb = rgba[:3].astype(np.float32) / RGB_MAX_VALUE
    alpha = float(rgba[3]) / RGB_MAX_VALUE
    luminance = float(np.dot(rgb, LUMINANCE_WEIGHTS))
    detail_weight = max(alpha, 1.0 - luminance)
    return LOCAL_PREVIEW_BASE_DEPTH + LOCAL_PREVIEW_DEPTH_VARIATION * detail_weight
