from pathlib import Path
from tempfile import TemporaryDirectory
import json

from fastapi.testclient import TestClient
from PIL import Image

from debug_agent.api import routes
from debug_agent.main import app


def test_artifact_image_route_serves_configured_crop_file() -> None:
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        temp_path = Path(temp_dir)
        artifact_path = temp_path / "case-1_box-7_localized-candidate.png"
        Image.new("RGB", (8, 6), color="white").save(artifact_path)
        original_artifact_dir = routes.settings.image_artifact_dir
        routes.settings.image_artifact_dir = temp_path
        try:
            client = TestClient(app)

            response = client.get("/artifacts/images/case-1_box-7_localized-candidate.png")

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            assert response.content
        finally:
            routes.settings.image_artifact_dir = original_artifact_dir


def test_artifact_manifest_route_serves_configured_json_file() -> None:
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        temp_path = Path(temp_dir)
        artifact_path = temp_path / "case-1_video_segment_1_delta.json"
        artifact_path.write_text(
            json.dumps({"manifest_type": "video_segment_delta", "target_id": "video:segment:1"}),
            encoding="utf-8",
        )
        original_artifact_dir = routes.settings.image_artifact_dir
        routes.settings.image_artifact_dir = temp_path
        try:
            client = TestClient(app)

            response = client.get("/artifacts/manifests/case-1_video_segment_1_delta.json")

            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            assert response.json() == {"manifest_type": "video_segment_delta", "target_id": "video:segment:1"}
        finally:
            routes.settings.image_artifact_dir = original_artifact_dir


def test_artifact_manifest_route_rejects_missing_or_unsafe_files() -> None:
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        original_artifact_dir = routes.settings.image_artifact_dir
        routes.settings.image_artifact_dir = Path(temp_dir)
        try:
            client = TestClient(app)

            missing_response = client.get("/artifacts/manifests/missing.json")
            unsafe_response = client.get("/artifacts/manifests/..%2Fsecret.json")

            assert missing_response.status_code == 404
            assert unsafe_response.status_code == 404
        finally:
            routes.settings.image_artifact_dir = original_artifact_dir
