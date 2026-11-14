"""Online TTS, per-character deterministic voice selection, honest inventory."""
import asyncio
from dataclasses import dataclass
from pathlib import Path
from .story import pick_voice_seed

LANG_PREFIXES = {
    'ru': ('ru-RU',), 'en': ('en-US', 'en-GB', 'en-AU'),
    'es': ('es-ES', 'es-MX'), 'it': ('it-IT',), 'de': ('de-DE',),
}
FALLBACK = {
    'ru': 'ru-RU-DmitryNeural', 'en': 'en-US-GuyNeural',
    'es': 'es-ES-AlvaroNeural', 'it': 'it-IT-DiegoNeural',
    'de': 'de-DE-ConradNeural',
}

@dataclass(frozen=True)
class Voice:
    name: str
    locale: str
    gender: str


async def get_voices(lang: str = 'all') -> list[Voice]:
    import edge_tts
    raw = await edge_tts.list_voices()
    prefixes = LANG_PREFIXES.get(lang)
    result = [Voice(name=v['ShortName'], locale=v.get('Locale', ''), gender=v.get('Gender', 'Unknown'))
              for v in raw if not prefixes or v.get('Locale', '').startswith(prefixes)]
    return sorted(result, key=lambda v: (v.locale, v.gender, v.name))


def choose_voice(voices: list[Voice], lang: str, character: str = 'narrator') -> str:
    prefixes = LANG_PREFIXES.get(lang, LANG_PREFIXES['en'])
    candidates = [v for v in voices if v.locale.startswith(prefixes)]
    if not candidates:
        return FALLBACK.get(lang, FALLBACK['en'])
    return candidates[pick_voice_seed(character) % len(candidates)].name


async def say(text: str, path: Path, voice: str, *, rate: str = '+0%', pitch: str = '+0Hz') -> None:
    import edge_tts
    if not text.strip():
        raise ValueError('Пустой текст озвучки.')
    path.parent.mkdir(parents=True, exist_ok=True)
    await edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch).save(str(path))
    if not path.is_file() or path.stat().st_size < 100:
        raise RuntimeError('Синтез речи не создал звуковой файл.')


def sync(coro):
    return asyncio.run(coro)
