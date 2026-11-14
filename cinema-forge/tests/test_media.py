from pathlib import Path
from PIL import Image
import pytest
from cinema_forge.media import poster, render_slide, concat_video, add_audio, ffmpeg
from cinema_forge.pipeline import Job, execute


def test_poster(tmp_path):
    dst = tmp_path / 'test.png'
    poster('Фотореалистичная гонка по Парижу', 1, 12, dst)
    assert Image.open(dst).size == (1280, 720)


def test_local_pipeline_tiny_no_network(tmp_path):
    # Real end-to-end FFmpeg render, shortened to a few seconds to keep CI fast.
    result = execute(Job('Blue sports car', tmp_path/'out.mp4',
                         profile='Preview 720p / 24 FPS', seconds=2, shot_seconds=1,
                         narration=False), log=lambda _: None)
    assert result.is_file() and result.stat().st_size > 2000
    with result.open('rb') as f:
        assert b'ftyp' in f.read(64)
    # Cache/resume the same job; finished scenes are reused.
    first = result.stat().st_size
    result2 = execute(Job('Blue sports car', tmp_path/'out.mp4',
                          profile='Preview 720p / 24 FPS', seconds=2, shot_seconds=1,
                          narration=False), log=lambda _: None)
    assert result2.stat().st_size == first


def test_invalid_output(tmp_path):
    with pytest.raises(ValueError):
        execute(Job('test', tmp_path/'foo.mov', narration=False), log=lambda _: None)


def test_cancel(tmp_path):
    import threading
    ev=threading.Event();ev.set()
    with pytest.raises(InterruptedError):
        execute(Job('test',tmp_path/'a.mp4',profile='Preview 720p / 24 FPS', narration=False),
                cancel=ev, log=lambda _: None)
