import pytest
from services.ytdlp import YtdlpService


@pytest.mark.asyncio
async def test_parse_url_returns_video_info():
    service = YtdlpService()
    result = await service.parse_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result.title is not None
    assert result.thumbnail is not None
    assert len(result.formats) > 0


@pytest.mark.asyncio
async def test_parse_url_invalid_returns_empty_formats():
    service = YtdlpService()
    result = await service.parse_url("https://invalid-url-that-does-not-exist.com")
    assert len(result.formats) == 0
