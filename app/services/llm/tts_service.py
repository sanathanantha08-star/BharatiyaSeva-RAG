import asyncio
import base64
import io
from gtts import gTTS


async def text_to_audio_base64(text: str, lang: str = "en") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _tts_sync, text, lang)


def _tts_sync(text: str, lang: str) -> str:
    buf = io.BytesIO()
    gTTS(text=text, lang=lang, slow=False).write_to_fp(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")