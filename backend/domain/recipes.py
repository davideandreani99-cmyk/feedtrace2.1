"""Versionamento ricette (RF-01): una modifica crea una nuova versione."""

from datetime import date, timedelta


def plan_new_version(
    current_version: int, current_valid_from: date, new_valid_from: date
) -> tuple[int, date]:
    """Restituisce (nuovo numero versione, valid_to della versione precedente).

    La nuova versione non può decorrere prima della precedente. Se decorre lo stesso
    giorno, la precedente risulta chiusa il giorno prima (mai in vigore, sostituita).
    """
    if new_valid_from < current_valid_from:
        raise ValueError("La nuova versione non può decorrere prima della precedente")
    return current_version + 1, new_valid_from - timedelta(days=1)
