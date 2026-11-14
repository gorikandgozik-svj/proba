"""Deterministic scene breakdown; deliberately not misrepresented as LLM scriptwriting."""
from dataclasses import dataclass
import hashlib
import re

SHOTS = (
    'Establishing wide shot, elegant slow dolly in, detailed environment.',
    'Medium composition, subtle tracking camera, natural light and motion.',
    'Intimate cinematic close-up, shallow depth of field, tactile detail.',
    'Dynamic lateral tracking shot, continuous natural movement.',
    'Wide atmospheric panorama, cinematic composition, soft volumetric light.',
    'Low-angle hero shot, rich contrast, realistic materials.',
    'Slow aerial reveal, physically plausible camera motion.',
    'Detail insert shot, macro textures, refined highlights.',
    'Character-focused medium shot, expressive body language.',
    'Wide cinematic action, precise choreography and coherent geography.',
    'Emotional close-up, restrained naturalism, shallow focus.',
    'Final sweeping crane shot, satisfying visual conclusion.',
)

RU_NARRATION = (
    'История начинается. В центре нашего внимания — {theme}.',
    'Мы приближаемся и замечаем то, что прежде было скрыто.',
    'Каждая деталь раскрывает характер этой истории.',
    'Движение наполняет происходящее энергией.',
    'Мир вокруг становится всё более выразительным.',
    'Наступает момент, когда многое меняется.',
    'Новая перспектива позволяет взглянуть шире.',
    'Именно детали создают подлинную атмосферу.',
    'Теперь всё внимание приковано к главному.',
    'История набирает силу и движется к развязке.',
    'Остаётся самое важное — ощущение момента.',
    'И этот финальный кадр завершает наше путешествие.',
)
EN_NARRATION = (
    'Our story begins. At its heart is {theme}.',
    'We move closer to discover what was hidden.',
    'Every detail reveals something new.',
    'Motion brings energy to the scene.',
    'The world grows increasingly expressive.',
    'This is where everything begins to change.',
    'A new perspective reveals the bigger picture.',
    'Small details create a powerful atmosphere.',
    'Now all eyes turn toward what matters.',
    'The story gathers momentum toward its conclusion.',
    'All that remains is the feeling of this moment.',
    'One final image brings our journey to a close.',
)


ES_NARRATION = (
    'Nuestra historia comienza. En el centro está {theme}.',
    'Nos acercamos y descubrimos algo inesperado.',
    'Cada detalle revela una parte de la historia.',
    'El movimiento llena de energía la escena.',
    'El mundo adquiere una atmósfera única.',
    'Ha llegado el momento en que todo cambia.',
    'Una nueva perspectiva amplía nuestra mirada.',
    'Los pequeños detalles crean la emoción.',
    'Ahora toda la atención se dirige al protagonista.',
    'La historia avanza hacia su desenlace.',
    'Solo importa la intensidad de este instante.',
    'La imagen final pone fin a nuestro viaje.',
)
IT_NARRATION = (
    'La nostra storia comincia. Al centro troviamo {theme}.',
    'Ci avviciniamo e scopriamo qualcosa di nuovo.',
    'Ogni dettaglio rivela un altro lato della storia.',
    'Il movimento dona energia alla scena.',
    'Il mondo diventa sempre più suggestivo.',
    'È arrivato il momento in cui tutto cambia.',
    'Una nuova prospettiva ci mostra il quadro completo.',
    'Sono i piccoli dettagli a creare l’atmosfera.',
    'Ora tutta l’attenzione va al protagonista.',
    'La storia si avvicina al suo finale.',
    'Ciò che resta è l’emozione del momento.',
    'Un’ultima immagine conclude il nostro viaggio.',
)
DE_NARRATION = (
    'Unsere Geschichte beginnt. Im Mittelpunkt steht {theme}.',
    'Wir kommen näher und entdecken etwas Neues.',
    'Jedes Detail zeigt eine andere Seite der Geschichte.',
    'Bewegung bringt Energie in die Szene.',
    'Die Atmosphäre wird immer eindrucksvoller.',
    'Jetzt beginnt sich alles zu verändern.',
    'Ein neuer Blickwinkel zeigt das große Ganze.',
    'Gerade kleine Details schaffen die Stimmung.',
    'Jetzt richtet sich alle Aufmerksamkeit auf das Wesentliche.',
    'Die Geschichte bewegt sich auf das Ende zu.',
    'Es bleibt das Gefühl dieses Augenblicks.',
    'Ein letztes Bild schließt unsere Reise ab.',
)
TEMPLATES = {'ru': RU_NARRATION, 'en': EN_NARRATION,
             'es': ES_NARRATION, 'it': IT_NARRATION, 'de': DE_NARRATION}

@dataclass(frozen=True)
class Scene:
    index: int
    seconds: int
    video_prompt: str
    narration: str


def guess_language(text: str) -> str:
    cyr = sum('\u0400' <= c <= '\u052f' for c in text)
    lat = sum('a' <= c.lower() <= 'z' for c in text)
    return 'ru' if cyr > lat else 'en'


def storyboard(prompt: str, *, seconds: int = 120, shot_seconds: int = 10, language: str = 'auto') -> list[Scene]:
    prompt = re.sub(r'\s+', ' ', prompt).strip()
    if not prompt or len(prompt) > 3500:
        raise ValueError('Промпт должен содержать от 1 до 3500 символов.')
    if seconds < 1 or seconds > 600 or shot_seconds < 1 or shot_seconds > 30:
        raise ValueError('Некорректная длительность или длина сцены.')
    lang = guess_language(prompt) if language == 'auto' else language
    template = TEMPLATES.get(lang, EN_NARRATION)
    theme = prompt[:65].rstrip('., ')  # Useful only as a simple, explicitly templated voiceover.
    durations = [shot_seconds] * (seconds // shot_seconds)
    if seconds % shot_seconds:
        durations.append(seconds % shot_seconds)
    scenes = []
    for i, duration in enumerate(durations):
        # Explicitly separate clip instructions; do not pretend full script/character continuity is solved.
        shot = SHOTS[i % len(SHOTS)]
        scene_prompt = (
            f'{prompt}\nShot {i+1}/{len(durations)}. {shot} '
            'Photorealistic live-action cinematography, realistic light and physics, '
            'consistent characters and wardrobes, no subtitles, no logos, no text overlays.'
        )
        narration = template[i % len(template)].format(theme=theme)
        scenes.append(Scene(index=i + 1, seconds=duration, video_prompt=scene_prompt, narration=narration))
    return scenes


def pick_voice_seed(label: str) -> int:
    return int(hashlib.sha256(label.encode('utf-8')).hexdigest()[:8], 16)
