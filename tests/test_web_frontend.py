from fastapi.testclient import TestClient
from io import BytesIO
from pathlib import Path

from PIL import Image


def test_frontend_shell_and_assets_are_public_but_api_remains_protected(
    monkeypatch, tmp_path
):
    import gateway.app as gateway_module

    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(
        "<!doctype html><title>ACIS Vue</title>", encoding="utf-8"
    )
    (tmp_path / "assets" / "app.js").write_text("console.log('acis')", encoding="utf-8")
    monkeypatch.setattr(gateway_module, "WEB_DIST_DIR", tmp_path, raising=False)
    monkeypatch.setenv("ACIS_API_KEY", "test-key-" + "x" * 32)
    client = TestClient(gateway_module.app)

    assert client.get("/").status_code == 200
    assert "ACIS Vue" in client.get("/").text
    assert client.get("/assets/app.js").text == "console.log('acis')"
    assert client.get("/decisions").status_code == 401


def test_missing_frontend_build_does_not_break_api_routes(monkeypatch, tmp_path):
    import gateway.app as gateway_module

    monkeypatch.setattr(gateway_module, "WEB_DIST_DIR", tmp_path, raising=False)
    monkeypatch.setenv("ACIS_API_KEY", "test-key-" + "x" * 32)
    client = TestClient(gateway_module.app)

    assert client.get("/").status_code == 404
    assert client.get("/health").status_code == 200


def test_authenticated_image_upload_stages_image_and_diagnose_receives_path(
    monkeypatch, tmp_path
):
    import gateway.app as gateway_module

    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("ACIS_IMAGE_UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("ACIS_API_KEY", "test-key-" + "x" * 32)
    client = TestClient(gateway_module.app)
    image_buffer = BytesIO()
    Image.new("RGB", (2, 2), color="green").save(image_buffer, format="PNG")
    image_bytes = image_buffer.getvalue()
    headers = {
        "X-API-Key": "test-key-" + "x" * 32,
        "Content-Type": "image/png",
    }

    unauthorized = client.post("/images", content=image_bytes, headers={"Content-Type": "image/png"})
    assert unauthorized.status_code == 401

    uploaded = client.post("/images", content=image_bytes, headers=headers)
    assert uploaded.status_code == 200
    image_path = Path(uploaded.json()["image_path"])
    assert image_path.parent == upload_dir.resolve()
    assert image_path.is_file()
    assert image_path.read_bytes() == image_bytes

    observed = {}

    class CapturingOrchestrator:
        last_trace = None

        def __init__(self, **_kwargs):
            pass

        def run(self, query, image_path=None):
            observed.update(query=query, image_path=image_path)
            return object()

    monkeypatch.setattr(gateway_module, "AgentOrchestrator", CapturingOrchestrator)
    monkeypatch.setattr(
        gateway_module,
        "_decision_payload",
        lambda _decision, _trace: {"decision": "测试诊断"},
    )
    diagnosed = client.post(
        "/diagnose",
        headers={"X-API-Key": "test-key-" + "x" * 32},
        json={"query": "玉米叶片出现病斑", "image_path": str(image_path)},
    )

    assert diagnosed.status_code == 200
    assert observed == {"query": "玉米叶片出现病斑", "image_path": str(image_path)}


def test_image_upload_rejects_unsupported_mime_and_invalid_content(monkeypatch, tmp_path):
    import gateway.app as gateway_module

    monkeypatch.setenv("ACIS_IMAGE_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("ACIS_API_KEY", "test-key-" + "x" * 32)
    client = TestClient(gateway_module.app)
    headers = {"X-API-Key": "test-key-" + "x" * 32}

    unsupported = client.post(
        "/images", content=b"data", headers={**headers, "Content-Type": "image/gif"}
    )
    invalid = client.post(
        "/images", content=b"not an image", headers={**headers, "Content-Type": "image/png"}
    )

    assert unsupported.status_code == 415
    assert invalid.status_code == 422
    assert not (tmp_path / "uploads").exists()

