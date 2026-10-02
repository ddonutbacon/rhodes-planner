from __future__ import annotations


def fmt_num(value) -> str:
    """Format quantities cleanly for UI text.

    Whole numbers are rendered without decimals; fractional expected values
    keep up to two decimal places.
    """
    number = float(value)
    if abs(number - round(number)) < 1e-9:
        return f"{int(round(number)):,}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")
