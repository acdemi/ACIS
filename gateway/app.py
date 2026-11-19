"""FastAPI gateway for the agriculture Agent orchestrator."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _env import load_env
load_env()  # 注入 .env（DEEPSEEK_API_KEY / NEO4J_PASSWORD），须在 import orchestrator 前

import logging
import hmac
import os
import warnings
from io import BytesIO
from typing import Literal
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Path as APIPath, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from PIL import Image
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from orchestrator import AgentOrchestrator, _decision_payload
from utils.judge_runtime import resolve_judge_config

logger = logging.getLogger(__name__)

app = FastAPI(title="Agri AI Gateway", version="0.2.0")
WEB_DIST_DIR = ROOT / "web" / "dist"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_IMAGE_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".bmp": "BMP",
}
ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/bmp": ".bmp",
}
MIN_API_KEY_LENGTH = 32


def _api_key_is_valid(value: str) -> bool:
    try:
        return len(value.encode("ascii")) >= MIN_API_KEY_LENGTH
    except UnicodeEncodeError:
        return False


def _api_key_matches(provided: str, expected: str) -> bool:
    try:
        provided_bytes = provided.encode("ascii")
        expected_bytes = expected.encode("ascii")
    except UnicodeEncodeError:
        return False
    return hmac.compare_digest(provided_bytes, expected_bytes)


class DiagnoseRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    image_path: str | None = Field(default=None, max_length=512)
    use_llm_judge: bool = False
    use_llm_critic: bool = False


@app.middleware("http")
async def require_api_key(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    path = request.url.path
    public_frontend = (
        path == "/"
        or path.startswith("/assets/")
        or path == "/favicon.ico"
        or path == "/site.webmanifest"
    )
    if path != "/health" and not public_frontend:
        expected = os.environ.get("ACIS_API_KEY", "").strip()
        if not _api_key_is_valid(expected):
            return JSONResponse(
                status_code=503,
                content={"detail": "ACIS_API_KEY must contain at least 32 characters"},
            )
        provided = request.headers.get("X-API-Key", "")
        if not _api_key_matches(provided, expected):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


def _frontend_file(relative_path: str) -> Path:
    root = WEB_DIST_DIR.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=404, detail="frontend asset not found") from None
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="frontend asset not found")
    return candidate


def _validate_image_path(image_path: str | None) -> str | None:
    if image_path is None:
        return None

    upload_root = Path(
        os.environ.get("ACIS_IMAGE_UPLOAD_DIR", str(ROOT / "data" / "uploads"))
    ).resolve()
    try:
        candidate = Path(image_path).resolve(strict=True)
        candidate.relative_to(upload_root)
    except (OSError, RuntimeError, ValueError):
        raise HTTPException(
            status_code=422,
            detail="image_path must refer to a staged upload under the upload directory",
        ) from None

    suffix = candidate.suffix.lower()
    if not candidate.is_file() or suffix not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(status_code=422, detail="image_path is not a supported image")
    try:
        image_size = candidate.stat().st_size
    except OSError:
        raise HTTPException(status_code=422, detail="image_path is not accessible") from None
    if image_size > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image exceeds the 10 MiB limit")
    try:
        image_bytes = candidate.read_bytes()
    except OSError:
        raise HTTPException(status_code=422, detail="image_path is not accessible") from None
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image exceeds the 10 MiB limit")
    _validate_image_content(image_bytes, ALLOWED_IMAGE_FORMATS[suffix])
    return str(candidate)


def _validate_image_content(image_bytes: bytes, expected_format: str) -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_bytes)) as image:
                if image.format != expected_format:
                    raise HTTPException(
                        status_code=422,
                        detail="image content does not match its file extension",
                    )
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise HTTPException(
                        status_code=413, detail="image exceeds the 40 MP limit"
                    )
                image.verify()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(status_code=413, detail="image exceeds the 40 MP limit") from None
    except (OSError, SyntaxError, ValueError):
        raise HTTPException(status_code=422, detail="image content is invalid") from None


@app.post("/images")
async def upload_image(request: Request) -> dict[str, object]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    suffix = ALLOWED_IMAGE_MIME_TYPES.get(content_type)
    if suffix is None:
        raise HTTPException(status_code=415, detail="unsupported image content type")

    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid content length") from None
        if declared_size < 0:
            raise HTTPException(status_code=400, detail="invalid content length")
        if declared_size > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="image exceeds the 10 MiB limit")

    image_bytes = bytearray()
    async for chunk in request.stream():
        image_bytes.extend(chunk)
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="image exceeds the 10 MiB limit")
    if not image_bytes:
        raise HTTPException(status_code=422, detail="image content is empty")
    _validate_image_content(bytes(image_bytes), ALLOWED_IMAGE_FORMATS[suffix])

    upload_root = Path(
        os.environ.get("ACIS_IMAGE_UPLOAD_DIR", str(ROOT / "data" / "uploads"))
    ).resolve()
    target = upload_root / f"{uuid4().hex}{suffix}"
    try:
        upload_root.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as image_file:
            image_file.write(image_bytes)
    except OSError as exc:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        logger.error("image upload failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="image upload failed") from None

    return {
        "image_path": str(target.resolve()),
        "size_bytes": len(image_bytes),
        "content_type": content_type,
    }


@app.get("/health")
def health() -> dict[str, object]:
    """Report readiness and whether the optional LLM Judge is configured."""
    if not _api_key_is_valid(os.environ.get("ACIS_API_KEY", "").strip()):
        raise HTTPException(
            status_code=503,
            detail="ACIS_API_KEY must contain at least 32 characters",
        )
    return {"status": "ok", "judge_configured": resolve_judge_config().configured}


@app.post("/diagnose")
def diagnose(request: DiagnoseRequest) -> dict:
    image_path = _validate_image_path(request.image_path)
    try:
        orchestrator = AgentOrchestrator(
            use_llm_judge=request.use_llm_judge, use_llm_critic=request.use_llm_critic
        )
        decision = orchestrator.run(request.query, image_path)
        return _decision_payload(decision, orchestrator.last_trace)
    except ValueError as exc:
        logger.info("diagnose rejected: %s", type(exc).__name__)
        raise HTTPException(status_code=422, detail="invalid diagnosis input") from None
    except Exception as exc:  # boundary: never leak a bare 500/stack trace
        logger.error("diagnose failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail=f"diagnosis failed: {type(exc).__name__}",
        ) from None


@app.get("/decisions")
def list_decisions(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    from storage.repository import list_decisions as _list
    return _list(limit)


@app.get("/decisions/{decision_id}")
def get_decision(decision_id: int = APIPath(ge=1)) -> dict:
    from storage.repository import get_decision as _get
    d = _get(decision_id)
    if d is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return d

class FeedbackRequest(BaseModel):
    feedback: Literal["correct", "incorrect", "partial"]
    note: str = Field(default="", max_length=2000)


@app.post("/decisions/{decision_id}/feedback")
def set_feedback(
    decision_id: int = APIPath(ge=1), request: FeedbackRequest = ...
) -> dict:
    """人工复核反馈：标记决策正确/错误，回灌案例库。"""
    from storage.repository import set_feedback as _set
    d = _set(decision_id, request.feedback, request.note)
    if d is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return d


class OutcomeRequest(BaseModel):
    outcome: Literal["有效", "无效", "部分有效"]
    note: str = Field(default="", max_length=2000)


@app.post("/decisions/{decision_id}/outcome")
def set_outcome(
    decision_id: int = APIPath(ge=1), request: OutcomeRequest = ...
) -> dict:
    """ACIS 2.0: 记录决策实际结果（有效/无效/部分有效），供经验回放 Agent 召回。"""
    from storage.repository import set_outcome as _set
    d = _set(decision_id, request.outcome, request.note)
    if d is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return d


@app.get("/", include_in_schema=False)
def frontend_index():
    from fastapi.responses import FileResponse

    return FileResponse(_frontend_file("index.html"))


@app.get("/assets/{asset_path:path}", include_in_schema=False)
def frontend_asset(asset_path: str):
    from fastapi.responses import FileResponse

    return FileResponse(_frontend_file(f"assets/{asset_path}"))


@app.get("/favicon.ico", include_in_schema=False)
def frontend_favicon():
    from fastapi.responses import FileResponse

    return FileResponse(_frontend_file("favicon.ico"))
