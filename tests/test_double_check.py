import sys
import types

sys.modules.setdefault("openai", types.SimpleNamespace(OpenAI=lambda *a, **k: None))
sys.modules.setdefault("groq", types.SimpleNamespace(Groq=lambda *a, **k: None))

import ai.llm_manager as lm


def _make_mock(responses):
    calls = {"count": 0}

    def fake_once(*args, **kwargs):
        calls["count"] += 1
        return lm._sanitize_yes_no(responses.pop(0))

    return fake_once, calls


def test_sanitize_yes_no(monkeypatch):
    fake, calls = _make_mock(["Yes.  "])
    monkeypatch.setattr(lm, "_run_prompt_once", fake)
    assert lm.run_prompt("target_company_validation") == "Yes"
    assert calls["count"] == 1


def test_double_check_majority(monkeypatch):
    fake, calls = _make_mock(["Yes.", "No", "No"])
    monkeypatch.setattr(lm, "_run_prompt_once", fake)
    assert lm.run_prompt("target_company_validation", double_check=True) == "No"
    assert calls["count"] == 3


def test_double_check_early_exit(monkeypatch):
    fake, calls = _make_mock(["No", "No"])
    monkeypatch.setattr(lm, "_run_prompt_once", fake)
    assert lm.run_prompt("target_company_validation", double_check=True) == "No"
    assert calls["count"] == 2


def test_double_check_not_applied(monkeypatch):
    fake, calls = _make_mock(["Foo"])
    monkeypatch.setattr(lm, "_run_prompt_once", fake)
    lm.run_prompt("clients_of_contact", double_check=True)
    assert calls["count"] == 1
