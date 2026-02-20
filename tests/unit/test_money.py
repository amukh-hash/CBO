from app.domain.money import cents_to_money, parse_money_to_cents


def test_parse_money() -> None:
    assert parse_money_to_cents("$12.34") == 1234
    assert parse_money_to_cents("1,000") == 100000
    assert parse_money_to_cents("-2.5") == -250


def test_format_money() -> None:
    assert cents_to_money(1234) == "$12.34"
    assert cents_to_money(-250) == "-$2.50"
