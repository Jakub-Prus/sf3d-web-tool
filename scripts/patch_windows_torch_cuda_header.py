from __future__ import annotations

import platform
import sys
from pathlib import Path

PATCH_MARKER = "Windows CUDA build compatibility patch"
HEADER_RELATIVE_PATH = Path("include") / "torch" / "csrc" / "dynamo" / "compiled_autograd.h"
TARGET_SNIPPET = (
    "    } else if constexpr (::std::is_same_v<T, ::std::string>) {\n"
    "      return at::StringType::get();\n"
)
PATCHED_SNIPPET = (
    "    // Windows CUDA build compatibility patch: avoid MSVC C2872 'std' ambiguity in nvcc builds.\n"
    "    // } else if constexpr (::std::is_same_v<T, ::std::string>) {\n"
    "    //   return at::StringType::get();\n"
)


def _resolve_header_path() -> Path:
    import torch

    return Path(torch.__file__).resolve().parent / HEADER_RELATIVE_PATH


def main() -> int:
    if platform.system() != "Windows":
        print("Windows-specific patch skipped on non-Windows platform.")
        return 0

    header_path = _resolve_header_path()
    source = header_path.read_text(encoding="utf-8")
    if PATCH_MARKER in source:
        print(f"PyTorch header already patched: {header_path}")
        return 0
    if TARGET_SNIPPET not in source:
        print(
            f"Expected PyTorch header snippet was not found: {header_path}",
            file=sys.stderr,
        )
        return 1

    header_path.write_text(
        source.replace(TARGET_SNIPPET, PATCHED_SNIPPET),
        encoding="utf-8",
    )
    print(f"Patched PyTorch CUDA build header: {header_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
