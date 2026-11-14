"""Runway developer API provider. The API requires a valid paid key."""
import json
from pathlib import Path
import random
import time
from typing import Callable
import requests

API = 'https://api.dev.runwayml.com/v1'
VERSION = '2024-11-06'
MODEL = {
    'Kling 3.0 4K': ('kling3.0_4k', '3840:2160'),
    'Kling 3.0 Pro 1080p': ('kling3.0_pro', '1920:1080'),
    'Kling 3.0 Standard 720p': ('kling3.0_standard', '1280:720'),
    'Runway Gen-4.5 720p': ('gen4.5', '1280:720'),
}

# Official Runway Developer pricing, checked November 14, 2026.
# These are indicative charges, not an account balance or provider guarantee.
# Disabling model-native audio enables the lower Kling Standard/Pro prices.
from decimal import Decimal
USD_PER_SECOND = {
    'Kling 3.0 4K': Decimal('0.43'),
    'Kling 3.0 Pro 1080p': Decimal('0.12'),
    'Kling 3.0 Standard 720p': Decimal('0.09'),
    'Runway Gen-4.5 720p': Decimal('0.12'),
}

def estimate_usd(model_choice: str, duration: int = 120) -> Decimal:
    if model_choice not in USD_PER_SECOND or not 1 <= duration <= 600:
        raise ValueError('Неизвестная модель или недопустимая длительность.')
    return USD_PER_SECOND[model_choice] * duration


class CloudError(RuntimeError):
    pass


def _headers(key: str) -> dict[str, str]:
    if not key.strip():
        raise CloudError('Нужен действующий Runway API key: облачная AI-генерация платная.')
    return {'Authorization': f'Bearer {key.strip()}', 'X-Runway-Version': VERSION,
            'Content-Type': 'application/json'}


def _request(method: str, endpoint: str, key: str, payload=None, *, session=None):
    s = session or requests
    try:
        result = s.request(method, f'{API}{endpoint}', headers=_headers(key), json=payload, timeout=60)
        if result.status_code >= 400:
            detail = result.text[:400]
            raise CloudError(f'Runway API HTTP {result.status_code}: {detail}')
        return result.json()
    except requests.RequestException as e:
        raise CloudError(f'Ошибка сети Runway: {e}') from e


def generate(prompt: str, seconds: int, model_choice: str, api_key: str, output: Path,
             *, log: Callable[[str], None] = lambda _: None, cancel=None, session=None,
             poll_limit: int = 240, sleep=time.sleep) -> None:
    if model_choice not in MODEL:
        raise ValueError('Неизвестная модель генерации.')
    if not 2 <= seconds <= 10:
        # Deliberate simple 10s scene pipeline; API may support more with other models.
        raise ValueError('Для выбранного режима длительность сцены — 2–10 секунд.')
    model, ratio = MODEL[model_choice]
    payload = {'model': model, 'promptText': prompt[:1000], 'ratio': ratio, 'duration': seconds}
    # The application generates its own narrator track: avoid paying for discarded audio.
    if model.startswith('kling3.0_'):
        payload['audio'] = False
    created = _request('POST', '/text_to_video', api_key, payload, session=session)
    task_id = created.get('id')
    if not task_id:
        raise CloudError(f'Runway не вернул ID задачи: {str(created)[:300]}')
    log(f'Облачная задача создана: {task_id}')
    for attempt in range(poll_limit):
        if cancel is not None and cancel.is_set():
            try:
                _request('DELETE', f'/tasks/{task_id}', api_key, session=session)
            except Exception:
                pass
            raise InterruptedError('Отменено пользователем.')
        job = _request('GET', f'/tasks/{task_id}', api_key, session=session)
        status = job.get('status')
        if status == 'SUCCEEDED':
            links = job.get('output') or []
            if not links:
                raise CloudError('Runway сообщил SUCCEEDED, но не предоставил видео.')
            url = links[0]
            # Restricted to HTTPS and the URL returned by Runway; no user input URLs.
            if not isinstance(url, str) or not url.startswith('https://'):
                raise CloudError('Некорректный URL результата.')
            s = session or requests
            try:
                with s.get(url, stream=True, timeout=(20, 180)) as r:
                    r.raise_for_status()
                    output.parent.mkdir(parents=True, exist_ok=True)
                    partial = output.with_suffix('.partial')
                    with partial.open('wb') as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if cancel is not None and cancel.is_set():
                                raise InterruptedError('Отменено пользователем.')
                            if chunk:
                                f.write(chunk)
                    if partial.stat().st_size < 1024:
                        raise CloudError('Облачный ответ слишком мал для видео.')
                    partial.replace(output)
                    return
            except requests.RequestException as e:
                raise CloudError(f'Загрузка видео не удалась: {e}') from e
        if status in ('FAILED', 'CANCELED'):
            raise CloudError(f'Runway завершил задачу статусом {status}: {str(job.get("failure"))[:300]}')
        if status not in ('PENDING', 'RUNNING', 'THROTTLED'):
            raise CloudError(f'Неизвестный статус API: {status}')
        sleep(5 + random.random())
    raise CloudError('Превышено время ожидания API; задача может ещё выполняться в облаке.')
