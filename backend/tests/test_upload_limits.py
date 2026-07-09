from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
HTTPException = fastapi.HTTPException
pytest.importorskip("multipart")

from app.api import upload


class ChunkedUpload:
    def __init__(self, filename, chunks):
        self.filename = filename
        self.content_type = "video/mp4"
        self._chunks = list(chunks)

    async def read(self, _size):
        if self._chunks:
            return self._chunks.pop(0)
        return b""


def test_default_upload_limit_is_20gb(monkeypatch):
    monkeypatch.delenv("MAX_UPLOAD_SIZE_GB", raising=False)
    assert upload._parse_max_upload_size_gb() == 20
    assert upload._max_upload_size_bytes() == 20 * 1024 * 1024 * 1024


def test_zero_upload_limit_disables_app_limit(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE_GB", "0")
    assert upload._parse_max_upload_size_gb() == 0
    assert upload._max_upload_size_bytes() is None


def test_invalid_extension_is_rejected():
    with pytest.raises(HTTPException) as exc:
        upload._safe_upload_extension("video.avi")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_streaming_upload_removes_partial_file_when_limit_exceeded(tmp_path, monkeypatch):
    monkeypatch.setattr(upload, "UPLOAD_DIR", tmp_path.as_posix())
    monkeypatch.setenv("MAX_UPLOAD_SIZE_GB", str(1 / (1024 * 1024 * 1024)))
    fake_file = ChunkedUpload("large.mp4", [b"a", b"bc"])

    with pytest.raises(HTTPException) as exc:
        await upload._save_upload_file(fake_file, "analysis")

    assert exc.value.status_code == 413
    assert "Arquivo maior que o limite configurado" in exc.value.detail
    assert not list((tmp_path / "analysis").glob("*.mp4"))


@pytest.mark.asyncio
async def test_streaming_upload_allows_large_file_when_limit_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(upload, "UPLOAD_DIR", tmp_path.as_posix())
    monkeypatch.setenv("MAX_UPLOAD_SIZE_GB", "0")
    fake_file = ChunkedUpload("large.mp4", [b"a", b"bc"])

    saved_path = await upload._save_upload_file(fake_file, "analysis")

    assert Path(saved_path).read_bytes() == b"abc"
