from dataclasses import dataclass


@dataclass(frozen=True)
class PreprocessOptions:
    remove_background: bool
    auto_crop: bool
    normalize_size: bool


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
