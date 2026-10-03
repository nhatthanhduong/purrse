from __future__ import annotations

from decimal import Decimal, InvalidOperation


def _parse_thousand_vnd(value: str, allow_negative: bool) -> int:
    cleaned = value.strip().lower().replace(",", "").replace("đ", "")
    if cleaned.endswith("k"):
        cleaned = cleaned[:-1].strip()
    if not cleaned:
        raise ValueError("Enter an amount.")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Use a number such as 150 or 150.5.") from exc
    if not amount.is_finite() or (amount < 0 and not allow_negative):
        raise ValueError("Amount must be zero or greater.")
    vnd = amount * 1000
    if vnd != vnd.to_integral_value():
        raise ValueError("Use no more than three decimal places.")
    return int(vnd)


def parse_thousand_vnd(value: str) -> int:
    """Convert a non-negative thousand-VND input to exact whole VND."""
    return _parse_thousand_vnd(value, allow_negative=False)


def parse_signed_thousand_vnd(value: str) -> int:
    """Convert a possibly-negative bank balance in thousand VND."""
    return _parse_thousand_vnd(value, allow_negative=True)


def format_k(vnd: int, suffix: bool = True) -> str:
    value = Decimal(vnd) / Decimal(1000)
    text = f"{value:,.3f}".rstrip("0").rstrip(".")
    return f"{text}k" if suffix else text


def format_vnd(vnd: int) -> str:
    return f"{vnd:,.0f} VND"
