from pathlib import Path
from tempfile import TemporaryDirectory

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
