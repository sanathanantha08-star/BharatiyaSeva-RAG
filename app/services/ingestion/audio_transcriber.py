import whisper
import tempfile
import os
import asyncio

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("tiny")
    return _model


async def transcribe(audio_bytes: bytes, suffix: str = ".webm") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe_sync, audio_bytes, suffix)


def _transcribe_sync(audio_bytes: bytes, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        result = _get_model().transcribe(tmp_path, fp16=False, language="en")
        return result["text"].strip()
    finally:
        os.unlink(tmp_path)