"""Text-to-Speech via edge-tts (Microsoft Edge neural voices — free, no API key)."""
from __future__ import annotations

from typing import AsyncIterator

import edge_tts

# Neural voices — high quality, no cost
VOICES = {
    "es": "es-MX-DaliaNeural",   # Mexican Spanish, female, natural
    "en": "en-US-JennyNeural",   # US English, female, natural
}


class StreamingSynthesizer:
    async def synthesize_stream(self, text: str, lang: str = "es") -> AsyncIterator[bytes]:
        """Yields MP3 audio chunks as edge-tts generates them."""
        voice = VOICES.get(lang, VOICES["es"])
        communicate = edge_tts.Communicate(text, voice=voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
