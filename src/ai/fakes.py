"""Scriptable providers for gateway tests; never used in production."""

import copy


class FakeProvider:
    """Return a scripted result and record each request it receives."""

    def __init__(self, result):
        self.result = result
        self.calls = []

    def complete(self, instructions, data):
        """Record `instructions` and `data`, then return the scripted result."""
        self.calls.append((instructions, data))
        if callable(self.result):
            return self.result(instructions, data)
        return copy.deepcopy(self.result)
