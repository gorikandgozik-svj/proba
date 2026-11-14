import pytest
from cinema_forge.story import storyboard, guess_language, pick_voice_seed
from cinema_forge.voices import Voice, choose_voice


def test_duration_and_prompts():
    scenes = storyboard('A blue sports car in rain')
    assert len(scenes) == 12
    assert sum(s.seconds for s in scenes) == 120
    assert all(s.video_prompt and 'sports car' in s.video_prompt for s in scenes)
    assert scenes[0].narration != scenes[-1].narration


def test_short_remainder():
    scenes = storyboard('Тест', seconds=25, shot_seconds=10)
    assert [s.seconds for s in scenes] == [10, 10, 5]


def test_guess_language():
    assert guess_language('История про Луну') == 'ru'
    assert guess_language('A cinematic film') == 'en'


def test_reject_bad_prompts():
    with pytest.raises(ValueError):
        storyboard('  ')
    with pytest.raises(ValueError):
        storyboard('x' * 3501)
    with pytest.raises(ValueError):
        storyboard('hi', seconds=0)


def test_voice_choice_stable():
    voices = [Voice('ru-RU-A', 'ru-RU', 'Male'), Voice('ru-RU-B', 'ru-RU', 'Female')]
    assert choose_voice(voices, 'ru', 'maria') == choose_voice(voices, 'ru', 'maria')
    assert choose_voice(voices, 'de') == 'de-DE-ConradNeural'
