from brain import _safe_calculation, _time_answer
from voice import clean_text


def test_time_answer_uses_manila():
    assert "Philippine time" in _time_answer("What time is it?")


def test_safe_calculation():
    assert _safe_calculation("What is 137 * 42?") == "The answer is 5754."
    assert _safe_calculation("Calculate __import__('os').system('x')") is None


def test_tts_cleaning():
    assert clean_text("Hello **sir** https://example.com") == "Hello sir"


async def test_tts_cache_reuses_identical_text(tmp_path, monkeypatch):
    import voice

    class Settings:
        fish_api_key = "test-key"
        fish_voice_id = "test-voice"
        fish_model = "s2.1-pro"
        fish_speed = 1.0

    class FakeResponse:
        status_code = 200
        content = b"ID3fake-mp3"

    class FakeClient:
        calls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            self.calls += 1
            return FakeResponse()

    fake_client = FakeClient()
    monkeypatch.setattr(voice, "get_settings", lambda: Settings())
    monkeypatch.setattr(voice, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(voice.httpx, "AsyncClient", lambda **kwargs: fake_client)

    first = await voice.synthesize("Hello, sir.")
    second = await voice.synthesize("Hello, sir.")
    assert first == second == (b"ID3fake-mp3", "audio/mpeg")
    assert fake_client.calls == 1


def test_openjarvis_sdk_calls_groq_litellm_engine(monkeypatch):
    from types import SimpleNamespace

    import litellm

    from brain import _jarvis_call

    def fake_completion(**kwargs):
        assert kwargs["model"] == "groq/llama-3.3-70b-versatile"
        assert kwargs["messages"][0]["role"] == "system"
        assert "J.A.R.V.I.S." in kwargs["messages"][0]["content"]
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="At your service.", tool_calls=None
                    ),
                    finish_reason="stop",
                )
            ],
            usage=None,
            model=kwargs["model"],
        )

    monkeypatch.setattr(litellm, "completion", fake_completion)
    assert _jarvis_call("Test prompt", "llama-3.3-70b-versatile") == "At your service."
