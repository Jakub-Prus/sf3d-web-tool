from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image
from app.services.masking import detect_foreground_mask

LOCAL_PREVIEW_GRID_SIZE = 48
LOCAL_PREVIEW_BASE_DEPTH = 0.12
LOCAL_PREVIEW_DEPTH_VARIATION = 0.18
LOCAL_PREVIEW_MESH_NAME = "mesh.glb"
LOCAL_PREVIEW_MIN_OCCUPIED_CELLS = 1
LOCAL_PREVIEW_MIN_COMPONENT_AREA_RATIO = 0.004
LOCAL_PREVIEW_MASK_KERNEL_RATIO = 0.05
LOCAL_PREVIEW_HEIGHT_SMOOTHING_RATIO = 0.03
LOCAL_PREVIEW_BOTTOM_SCALE = 0.5
LOCAL_PREVIEW_BLUR_EPSILON = 1e-6
RGB_MAX_VALUE = 255.0
LUMINANCE_WEIGHTS = np.asarray([0.299, 0.587, 0.114], dtype=np.float32)
TOP_SURFACE_KEY = "top"
BOTTOM_SURFACE_KEY = "bottom"


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

    height_map = _build_height_map(rgba_array, occupancy_mask)
    mesh = _build_heightfield_mesh(height_map, occupancy_mask)
    mesh_path = artifact_dir / LOCAL_PREVIEW_MESH_NAME
    mesh.export(mesh_path)

    return LocalPreviewGenerationResult(
        mesh_path=mesh_path,
        occupied_cells=occupied_cell_count,
        notes=[
            "Local preview mode generated a deterministic smoothed heightfield extrusion because the official SF3D runner is unavailable.",
            segmentation_note,
            (
                f"Local preview mesh grid size: {preview_image.size[0]}x{preview_image.size[1]} "
                f"with {occupied_cell_count} occupied cells."
            ),
        ],
    )


def _resize_for_preview(image: Image.Image, grid_size: int) -> Image.Image:
    source_width, source_height = image.size
    scale = min(grid_size / source_width, grid_size / source_height)
    resized_width = max(1, round(source_width * scale))
    resized_height = max(1, round(source_height * scale))
    return image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)


def _build_occupancy_mask(rgba_array: np.ndarray) -> tuple[np.ndarray, str]:
    mask_result = detect_foreground_mask(Image.fromarray(rgba_array))
    if not mask_result.confident:
        return (
            mask_result.foreground_mask,
            "Local preview fallback could not isolate the foreground, so the full image canvas was extruded.",
        )

    refined_mask = _refine_preview_mask(mask_result.foreground_mask)
    if np.any(refined_mask):
        return (
            refined_mask,
            f"{mask_result.note} Local preview refined the mask for smoother silhouette meshing.",
        )
    return mask_result.foreground_mask, mask_result.note


def _refine_preview_mask(occupancy_mask: np.ndarray) -> np.ndarray:
    mask_uint8 = occupancy_mask.astype(np.uint8)
    kernel_size = _compute_kernel_size(*occupancy_mask.shape)
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    refined_mask = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel)
    refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_OPEN, kernel)

    component_count, component_labels, component_stats, _ = cv2.connectedComponentsWithStats(
        refined_mask,
        connectivity=8,
    )
    if component_count <= 1:
        return refined_mask > 0

    minimum_component_area = max(
        1,
        round(occupancy_mask.size * LOCAL_PREVIEW_MIN_COMPONENT_AREA_RATIO),
    )
    filtered_mask = np.zeros(occupancy_mask.shape, dtype=bool)
    for component_index in range(1, component_count):
        component_area = int(component_stats[component_index, cv2.CC_STAT_AREA])
        if component_area >= minimum_component_area:
            filtered_mask |= component_labels == component_index

    return filtered_mask if np.any(filtered_mask) else refined_mask > 0


def _build_height_map(rgba_array: np.ndarray, occupancy_mask: np.ndarray) -> np.ndarray:
    rgb = rgba_array[..., :3].astype(np.float32) / RGB_MAX_VALUE
    alpha = rgba_array[..., 3].astype(np.float32) / RGB_MAX_VALUE
    luminance = np.tensordot(rgb, LUMINANCE_WEIGHTS, axes=([-1], [0]))
    detail_weight = np.maximum(alpha, 1.0 - luminance)
    raw_height_map = (LOCAL_PREVIEW_BASE_DEPTH + LOCAL_PREVIEW_DEPTH_VARIATION * detail_weight) * occupancy_mask

    smoothing_sigma = max(
        0.6,
        min(occupancy_mask.shape) * LOCAL_PREVIEW_HEIGHT_SMOOTHING_RATIO,
    )
    blurred_height = cv2.GaussianBlur(raw_height_map, (0, 0), smoothing_sigma)
    blurred_mask = cv2.GaussianBlur(occupancy_mask.astype(np.float32), (0, 0), smoothing_sigma)
    smoothed_height_map = np.where(
        blurred_mask > LOCAL_PREVIEW_BLUR_EPSILON,
        blurred_height / np.maximum(blurred_mask, LOCAL_PREVIEW_BLUR_EPSILON),
        0.0,
    )

    return np.where(
        occupancy_mask,
        np.maximum(smoothed_height_map, LOCAL_PREVIEW_BASE_DEPTH),
        0.0,
    )


def _build_heightfield_mesh(height_map: np.ndarray, occupancy_mask: np.ndarray) -> trimesh.Trimesh:
    image_height, image_width = occupancy_mask.shape
    cell_width = 1.0 / image_width
    cell_height = 1.0 / image_height
    bottom_z = -LOCAL_PREVIEW_BASE_DEPTH * LOCAL_PREVIEW_BOTTOM_SCALE
    corner_heights = _build_corner_heights(height_map, occupancy_mask)
    vertex_lookup: dict[tuple[str, int, int], int] = {}
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []

    for row_index in range(image_height):
        for column_index in range(image_width):
            if not occupancy_mask[row_index, column_index]:
                continue

            top_corners = _get_cell_vertex_indices(
                vertex_lookup=vertex_lookup,
                vertices=vertices,
                surface_key=TOP_SURFACE_KEY,
                row_index=row_index,
                column_index=column_index,
                cell_width=cell_width,
                cell_height=cell_height,
                corner_heights=corner_heights,
                z_override=None,
            )
            bottom_corners = _get_cell_vertex_indices(
                vertex_lookup=vertex_lookup,
                vertices=vertices,
                surface_key=BOTTOM_SURFACE_KEY,
                row_index=row_index,
                column_index=column_index,
                cell_width=cell_width,
                cell_height=cell_height,
                corner_heights=corner_heights,
                z_override=bottom_z,
            )
            _add_quad_faces(faces, top_corners, flip_winding=False)
            _add_quad_faces(faces, bottom_corners, flip_winding=True)

            if row_index == 0 or not occupancy_mask[row_index - 1, column_index]:
                _add_quad_faces(faces, (bottom_corners[0], bottom_corners[1], top_corners[1], top_corners[0]))
            if row_index == image_height - 1 or not occupancy_mask[row_index + 1, column_index]:
                _add_quad_faces(faces, (bottom_corners[3], bottom_corners[2], top_corners[2], top_corners[3]))
            if column_index == 0 or not occupancy_mask[row_index, column_index - 1]:
                _add_quad_faces(faces, (bottom_corners[0], top_corners[0], top_corners[3], bottom_corners[3]))
            if column_index == image_width - 1 or not occupancy_mask[row_index, column_index + 1]:
                _add_quad_faces(faces, (bottom_corners[1], bottom_corners[2], top_corners[2], top_corners[1]))

    if not faces:
        raise ValueError("Local preview mesh generation expected at least one occupied cell.")

    mesh = trimesh.Trimesh(
        vertices=np.asarray(vertices, dtype=np.float32),
        faces=np.asarray(faces, dtype=np.int64),
        process=False,
    )
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    return mesh


def _build_corner_heights(height_map: np.ndarray, occupancy_mask: np.ndarray) -> np.ndarray:
    image_height, image_width = occupancy_mask.shape
    corner_height_sum = np.zeros((image_height + 1, image_width + 1), dtype=np.float32)
    corner_height_count = np.zeros((image_height + 1, image_width + 1), dtype=np.float32)
    weighted_height_map = height_map * occupancy_mask

    for row_offset in (0, 1):
        for column_offset in (0, 1):
            corner_height_sum[
                row_offset : row_offset + image_height,
                column_offset : column_offset + image_width,
            ] += weighted_height_map
            corner_height_count[
                row_offset : row_offset + image_height,
                column_offset : column_offset + image_width,
            ] += occupancy_mask

    return np.where(
        corner_height_count > LOCAL_PREVIEW_BLUR_EPSILON,
        corner_height_sum / np.maximum(corner_height_count, LOCAL_PREVIEW_BLUR_EPSILON),
        0.0,
    )


def _get_cell_vertex_indices(
    *,
    vertex_lookup: dict[tuple[str, int, int], int],
    vertices: list[tuple[float, float, float]],
    surface_key: str,
    row_index: int,
    column_index: int,
    cell_width: float,
    cell_height: float,
    corner_heights: np.ndarray,
    z_override: float | None,
) -> tuple[int, int, int, int]:
    corner_positions = (
        (row_index, column_index),
        (row_index, column_index + 1),
        (row_index + 1, column_index + 1),
        (row_index + 1, column_index),
    )
    vertex_indices: list[int] = []
    for vertex_row, vertex_column in corner_positions:
        vertex_key = (surface_key, vertex_row, vertex_column)
        if vertex_key not in vertex_lookup:
            x_position = vertex_column * cell_width - 0.5
            y_position = 0.5 - vertex_row * cell_height
            z_position = (
                z_override
                if z_override is not None
                else float(corner_heights[vertex_row, vertex_column])
            )
            vertex_lookup[vertex_key] = len(vertices)
            vertices.append((x_position, y_position, z_position))
        vertex_indices.append(vertex_lookup[vertex_key])

    return tuple(vertex_indices)


def _add_quad_faces(
    faces: list[tuple[int, int, int]],
    quad_indices: tuple[int, int, int, int],
    *,
    flip_winding: bool = False,
) -> None:
    if flip_winding:
        faces.append((quad_indices[0], quad_indices[2], quad_indices[1]))
        faces.append((quad_indices[0], quad_indices[3], quad_indices[2]))
        return

    faces.append((quad_indices[0], quad_indices[1], quad_indices[2]))
    faces.append((quad_indices[0], quad_indices[2], quad_indices[3]))


def _compute_kernel_size(image_height: int, image_width: int) -> int:
    kernel_size = max(3, round(min(image_height, image_width) * LOCAL_PREVIEW_MASK_KERNEL_RATIO))
    if kernel_size % 2 == 0:
        kernel_size += 1
    return kernel_size
