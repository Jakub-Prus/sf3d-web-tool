from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.config import Settings

RunnerDevice = Literal["cpu", "cuda"]


@dataclass(frozen=True)
class RuntimeDiagnostics:
    torch_version: str | None
    cuda_available: bool
    cuda_device_name: str | None
    cuda_extension_ready: bool
    sf3d_force_cpu: bool
    expected_runner_device: RunnerDevice


def get_runtime_diagnostics(settings: Settings) -> RuntimeDiagnostics:
    try:
        import torch
    except ImportError:
        return RuntimeDiagnostics(
            torch_version=None,
            cuda_available=False,
            cuda_device_name=None,
            cuda_extension_ready=False,
            sf3d_force_cpu=settings.sf3d_force_cpu,
            expected_runner_device="cpu",
        )

    cuda_available = bool(torch.cuda.is_available())
    cuda_device_name = torch.cuda.get_device_name(0) if cuda_available and torch.cuda.device_count() > 0 else None
    cuda_extension_ready = False
    if cuda_available:
        try:
            import texture_baker  # noqa: F401

            cuda_extension_ready = bool(
                torch._C._dispatch_has_kernel_for_dispatch_key(
                    "texture_baker_cpp::rasterize",
                    "CUDA",
                )
            )
        except (ImportError, RuntimeError, AttributeError):
            cuda_extension_ready = False
    expected_runner_device: RunnerDevice = (
        "cpu"
        if settings.sf3d_force_cpu or not cuda_available or not cuda_extension_ready
        else "cuda"
    )
    return RuntimeDiagnostics(
        torch_version=torch.__version__,
        cuda_available=cuda_available,
        cuda_device_name=cuda_device_name,
        cuda_extension_ready=cuda_extension_ready,
        sf3d_force_cpu=settings.sf3d_force_cpu,
        expected_runner_device=expected_runner_device,
    )
