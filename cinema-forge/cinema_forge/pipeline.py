"""Single prompt to resumable project render. No background promise: runs until process exits."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import threading
from typing import Callable
from .story import storyboard, guess_language
from .media import PROFILES, poster, render_slide, normalize_video, concat_video, add_audio, ffmpeg
from .voices import get_voices, choose_voice, say, sync
from .cloud import generate, MODEL

@dataclass
class Job:
    prompt: str
    destination: Path
    mode: str = 'Preview (motion graphics)'
    model: str = 'Kling 3.0 4K'
    profile: str = '4K UHD / 60 FPS'
    language: str = 'auto'
    narration: bool = True
    api_key: str = ''
    seconds: int = 120
    shot_seconds: int = 10


def execute(job: Job, *, log: Callable[[str], None] = print,
            progress: Callable[[float], None] = lambda _: None,
            cancel: threading.Event | None = None) -> Path:
    if job.profile not in PROFILES:
        raise ValueError('Некорректный профиль экспорта.')
    if job.mode not in ('Preview (motion graphics)', 'Cloud AI video'):
        raise ValueError('Некорректный режим.')
    if job.mode == 'Cloud AI video' and (job.model not in MODEL or not job.api_key.strip()):
        raise ValueError('Для облачной AI-генерации необходимо выбрать модель и указать Runway API key.')
    scenes = storyboard(job.prompt, seconds=job.seconds, shot_seconds=job.shot_seconds,
                        language=job.language)
    if job.mode == 'Cloud AI video' and any(s.seconds < 2 or s.seconds > 10 for s in scenes):
        raise ValueError('Для выбранных моделей сцены должны длиться от 2 до 10 секунд.')
    if job.destination.suffix.lower() != '.mp4':
        raise ValueError('Файл результата должен иметь расширение .mp4')
    job.destination.parent.mkdir(parents=True, exist_ok=True)
    spec = {'prompt': job.prompt, 'model': job.model if job.mode == 'Cloud AI video' else 'preview',
            'profile': job.profile, 'seconds': job.seconds, 'shot_seconds': job.shot_seconds,
            'narration': job.narration, 'language': job.language}
    fingerprint = hashlib.sha256(json.dumps(spec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    workspace = job.destination.parent / '.cinema_forge' / fingerprint
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / 'project.json').write_text(json.dumps({**spec, 'scenes': [s.__dict__ for s in scenes]},
                                                 ensure_ascii=False, indent=2), encoding='utf-8')
    log(f'FFmpeg: {ffmpeg()}')
    log(f'Проект: {workspace}')
    lang = guess_language(job.prompt) if job.language == 'auto' else job.language
    voices = []
    if job.narration:
        log('Получение списка доступных онлайн-нейроголосов...')
        voices = sync(get_voices(lang))
        log(f'Реальных доступных голосов для {lang}: {len(voices)}')
    ready = []
    voice_tracks = []
    cursor = 0
    for n, scene in enumerate(scenes):
        if cancel is not None and cancel.is_set():
            raise InterruptedError('Операция отменена пользователем.')
        log(f'Сцена {scene.index}/{len(scenes)} ({scene.seconds} сек)')
        raw = workspace / f'raw_{scene.index:02d}.mp4'
        normalized = workspace / f'clip_{scene.index:02d}.mp4'
        if not normalized.is_file() or normalized.stat().st_size < 1024:
            if job.mode == 'Preview (motion graphics)':
                img = workspace / f'poster_{scene.index:02d}.png'
                if not img.is_file():
                    poster(job.prompt, scene.index, len(scenes), img)
                render_slide(img, normalized, scene.seconds, job.profile, cancel=cancel, logger=log)
            else:
                if not raw.is_file() or raw.stat().st_size < 1024:
                    generate(scene.video_prompt, scene.seconds, job.model, job.api_key, raw,
                             log=log, cancel=cancel)
                normalize_video(raw, normalized, scene.seconds, job.profile, cancel=cancel, logger=log)
        ready.append(normalized)
        if job.narration:
            mp3 = workspace / f'voice_{scene.index:02d}.mp3'
            if not mp3.is_file() or mp3.stat().st_size < 100:
                # One narrator is used for the basic storyboard; character-cast inference is not claimed.
                selected = choose_voice(voices, lang, 'narrator')
                log(f'Озвучка: {selected}')
                sync(say(scene.narration, mp3, selected))
            voice_tracks.append((mp3, cursor))
        cursor += scene.seconds
        progress((n + 1) / (len(scenes) + 2))
    assembled = workspace / 'joined.mp4'
    if not assembled.is_file() or assembled.stat().st_size < 1024:
        concat_video(ready, assembled, cancel=cancel, logger=log)
    progress((len(scenes) + 1) / (len(scenes) + 2))
    log('Сборка звука, перенос MOOV в начало файла...')
    partial = job.destination.with_suffix('.partial.mp4')
    add_audio(assembled, voice_tracks, partial, job.seconds, cancel=cancel, logger=log)
    if not partial.is_file() or partial.stat().st_size < 1024:
        raise RuntimeError('Финальный MP4 не был создан.')
    partial.replace(job.destination)
    progress(1.0)
    log(f'ГОТОВО: {job.destination} ({job.destination.stat().st_size / 1048576:.1f} МиБ)')
    return job.destination
