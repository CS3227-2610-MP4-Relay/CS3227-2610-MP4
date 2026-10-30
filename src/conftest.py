"""Fixtures shared by every application test under `src/`."""

import os

import pytest

from ai import gateway


class _BlockedNetwork:
    """A stand-in for the gateway's network step that records and refuses calls."""

    def __init__(self):
        self.attempts = []

    def __call__(self, *args, **kwargs):
        self.attempts.append(args[:1])
        raise RuntimeError("Tests must not open an LLM provider connection.")


@pytest.fixture(autouse=True)
def block_llm_network(request, monkeypatch):
    """Remove SOC_LLM_* and block the gateway's network step unless opted in.

    A test marked `llm_transport` may use the transport, against a local server
    only. Any other test that reaches the network step fails at teardown, even
    when the code under test swallowed the error.
    """
    for name in list(os.environ):
        if name.startswith("SOC_LLM_"):
            monkeypatch.delenv(name)
    if request.node.get_closest_marker("llm_transport"):
        yield None
        return
    blocked = _BlockedNetwork()
    monkeypatch.setattr(gateway, "_exchange", blocked)
    yield blocked
    assert not blocked.attempts, "A test reached the LLM gateway's network step."
