from db import like_pattern
from forms import read_number, read_text, read_checkbox


def test_read_number_turns_text_into_a_number():
    assert read_number(" 15 ", lowest=1) == (15, True)


def test_read_number_allows_an_empty_box():
    assert read_number("", lowest=0) == (None, True)


def test_read_number_rejects_bad_text_and_out_of_range():
    assert read_number("two", lowest=0) == (None, False)
    assert read_number("-1", lowest=0) == (None, False)
    assert read_number("6", lowest=1, highest=5) == (None, False)


def test_read_text_trims_and_turns_blank_into_none():
    assert read_text({"brand": "  Mr. Color "}, "brand") == "Mr. Color"
    assert read_text({"brand": "   "}, "brand") is None
    assert read_text({}, "brand") is None


def test_read_checkbox():
    assert read_checkbox({"running_low": "on"}, "running_low") == 1
    assert read_checkbox({}, "running_low") == 0


def test_like_pattern_escapes_wildcards():
    assert like_pattern("exia") == "%exia%"
    assert like_pattern("100%") == "%100\\%%"
    assert like_pattern("Zaku_II") == "%Zaku\\_II%"