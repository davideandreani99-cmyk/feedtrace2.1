"""Parsing di valori in formato italiano (import CSV/XLSX). RF-01, RF-06."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

_TRUE = {"1", "true", "t", "si", "sì", "s", "y", "yes", "x", "vero"}
_FALSE = {"0", "false", "f", "no", "n", "", "falso"}
_DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")


def parse_bool_it(text: str) -> bool:
    value = text.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError(f"Valore sì/no non valido: {text!r}")


def parse_decimal_it(text: str) -> Decimal:
    """Accetta '12,5', '12.5', '1.234,56', '1,234.56'. Mai float."""
    s = text.strip().replace(" ", "").replace(" ", "")
    if not s:
        raise ValueError("Numero vuoto")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        value = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Numero non valido: {text!r}") from None
    if not value.is_finite():
        raise ValueError(f"Numero non valido: {text!r}")
    return value


def parse_date_it(text: str) -> date:
    s = text.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Data non valida: {text!r} (usa gg/mm/aaaa)")
