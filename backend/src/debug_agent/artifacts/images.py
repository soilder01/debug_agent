from pathlib import Path
from urllib.parse import unquote, urlparse

from PIL import Image
from pydantic import BaseModel


class ImageRegion(BaseModel):
    x: int
    y: int
    width: int
    height: int
    unit: str = "pixel"
    label: str = ""


class ImageArtifact(BaseModel):
    artifact_id: str
    kind: str
    source_image_uri: str
    region: ImageRegion | None = None
    derived_image_uri: str = ""


def materialize_image_crop(
    source_image_uri: str,
    region: ImageRegion,
    output_dir: Path,
    artifact_id: str,
) -> str:
    if region.unit != "pixel":
        raise ValueError(f"Unsupported image region unit: {region.unit}")

    source_path = _path_from_file_uri(source_image_uri)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{_safe_artifact_filename(artifact_id)}.png"
    with Image.open(source_path) as image:
        crop = image.crop((region.x, region.y, region.x + region.width, region.y + region.height))
        crop.save(output_path, format="PNG")
    return output_path.resolve().as_uri()


def _path_from_file_uri(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError(f"Only file:// image URIs can be cropped: {uri}")
    path_text = unquote(parsed.path)
    if len(path_text) >= 3 and path_text[0] == "/" and path_text[2] == ":":
        path_text = path_text[1:]
    return Path(path_text)


def _safe_artifact_filename(artifact_id: str) -> str:
    return "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in artifact_id)
