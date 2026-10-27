"""Tests for the text field shared by every round form."""

import pytest
from django.core.exceptions import ValidationError

from rounds.forms import RoundTextField


@pytest.mark.ac("RND-2.4")
def test_a_browser_line_break_counts_as_one_character():
    field = RoundTextField(max_length=5)
    assert field.clean("ab\r\ncd") == "ab\ncd"
    assert field.clean("\r\nab\r\n") == "ab"
    with pytest.raises(ValidationError) as refused:
        field.clean("abc\r\ncd")
    assert refused.value.messages == ["Enter 1 to 5 characters."]


def test_a_lone_carriage_return_is_kept():
    assert RoundTextField(max_length=5).clean("ab\rcd") == "ab\rcd"
