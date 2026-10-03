import pytest

from purrse.money import format_k, parse_signed_thousand_vnd, parse_thousand_vnd


def test_thousand_vnd_parser_uses_k_as_default_unit():
    assert parse_thousand_vnd("150") == 150_000
    assert parse_thousand_vnd("150.5k") == 150_500
    assert parse_thousand_vnd("1,250") == 1_250_000


@pytest.mark.parametrize("value", ["", "hello", "-1", "0.0001"])
def test_invalid_amounts_are_rejected(value):
    with pytest.raises(ValueError):
        parse_thousand_vnd(value)


def test_format_k_is_compact_and_exact():
    assert format_k(150_000) == "150k"
    assert format_k(-1_250_500) == "-1,250.5k"


def test_bank_balance_can_be_negative():
    assert parse_signed_thousand_vnd("-150.5") == -150_500
