"""Local dotenv parsing using synthetic files only; never inspect root dotenv."""

import os
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from relay.settings import dotenv

pytestmark = pytest.mark.ac("PLT-1.4")


@pytest.fixture
def file(tmp_path, monkeypatch):
    for name in dotenv.NAMES:
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / "synthetic.env"
    monkeypatch.setattr(dotenv, "DOTENV_PATH", path)
    return path


def test_literals_duplicates_empty_and_comments(file, monkeypatch):
    monkeypatch.setenv("SOC_LLM_MODEL", "process-model")
    file.write_text(
        " # comment\n\n export SOC_LLM_ENDPOINT = https://synthetic.invalid/chat \n"
        "SOC_LLM_API_KEY=first\nSOC_LLM_API_KEY='${SOC_LLM_MODEL}\\n#literal'\n"
        'POSTGRES_PASSWORD = " quoted literal "\nPOSTGRES_USER=\n',
        encoding="utf-8",
    )
    dotenv.load_dotenv()
    assert os.environ["SOC_LLM_API_KEY"] == "${SOC_LLM_MODEL}\\n#literal"
    assert os.environ["SOC_LLM_MODEL"] == "process-model"
    assert os.environ["POSTGRES_PASSWORD"] == " quoted literal "
    assert os.environ["POSTGRES_USER"] == ""
    assert os.environ["SOC_LLM_ENDPOINT"] == "https://synthetic.invalid/chat"


def test_unknown_names_cannot_configure_settings_or_process(file, monkeypatch):
    names = [
        "DJANGO_SETTINGS_MODULE",
        "PYTHONPATH",
        "SSLKEYLOGFILE",
        "DATABASE_URL",
        "SOC_LLM_LIVE",
        "ARBITRARY",
    ]
    for name in names:
        monkeypatch.delenv(name, raising=False)
    file.write_text("\n".join(f"{name}='ignored" for name in names))
    dotenv.load_dotenv()
    assert not set(names) & os.environ.keys()


@pytest.mark.parametrize(
    "line",
    [
        "SOC_LLM_API_KEY",
        "export SOC_LLM_API_KEY synthetic-sensitive",
        "SOC_LLM_API_KEY='synthetic-sensitive",
        'SOC_LLM_API_KEY=synthetic-sensitive"',
        'SOC_LLM_API_KEY="synthetic-sensitive" trailing',
        "SOC_LLM_API_KEY=synthetic-sensitive\x00",
    ],
)
def test_malformed_allowed_values_fail_without_leaking_or_partial_load(file, line):
    file.write_text(f"SOC_LLM_MODEL=synthetic-model\n{line}\n")
    with pytest.raises(ImproperlyConfigured) as caught:
        dotenv.load_dotenv()
    assert str(caught.value) == dotenv.ERROR
    assert "synthetic-sensitive" not in str(caught.value)
    assert "SOC_LLM_MODEL" not in os.environ


def test_missing_file_is_optional(file):
    dotenv.load_dotenv()
    assert not dotenv.NAMES & os.environ.keys()


def test_invalid_utf8_is_a_fixed_failure(file):
    file.write_bytes(b"SOC_LLM_API_KEY=\xff")
    with pytest.raises(ImproperlyConfigured, match=dotenv.ERROR):
        dotenv.load_dotenv()


@pytest.mark.parametrize(
    "failure", [OSError("synthetic-sensitive"), UnicodeError("synthetic-sensitive")]
)
def test_read_errors_have_no_value_or_exception_chain(file, monkeypatch, failure):
    def unreadable(*args, **kwargs):
        raise failure

    monkeypatch.setattr(Path, "read_text", unreadable)
    with pytest.raises(ImproperlyConfigured) as caught:
        dotenv.load_dotenv()
    assert str(caught.value) == dotenv.ERROR
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def test_fixed_root_path_is_independent_of_cwd_without_reading_it(
    tmp_path, monkeypatch
):
    seen = []

    def synthetic_read(path, **kwargs):
        seen.append(path)
        return "# synthetic only"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "read_text", synthetic_read)
    dotenv.load_dotenv()
    assert seen == [Path(__file__).resolve().parents[3] / ".env"]
