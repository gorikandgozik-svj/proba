from pathlib import Path
import pytest
from cinema_forge import cloud

class Reply:
    status_code = 200
    text = ''
    def __init__(self, value): self.value = value
    def json(self): return self.value

class FakeSession:
    def __init__(self, replies): self.replies = iter(replies); self.calls = []
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return Reply(next(self.replies))


def test_api_headers():
    with pytest.raises(cloud.CloudError):
        cloud._headers('')
    assert cloud._headers('secret')['X-Runway-Version'] == '2024-11-06'


def test_create_and_poll_failure(tmp_path):
    sess = FakeSession([{'id': 'test-task'}, {'status': 'FAILED', 'failure': 'quota'}])
    with pytest.raises(cloud.CloudError, match='FAILED'):
        cloud.generate('one prompt', 10, 'Kling 3.0 4K', 'secret', tmp_path/'out.mp4',
                       session=sess, sleep=lambda _: None)
    assert sess.calls[0][0] == 'POST'
    assert sess.calls[0][2]['json']['ratio'] == '3840:2160'


def test_invalid_model_or_duration(tmp_path):
    with pytest.raises(ValueError):
        cloud.generate('hi', 10, 'UNKNOWN', 'abc', tmp_path/'v.mp4')
    with pytest.raises(ValueError):
        cloud.generate('hi', 15, 'Kling 3.0 4K', 'abc', tmp_path/'v.mp4')
