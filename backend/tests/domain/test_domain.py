from datetime import date
from decimal import Decimal

import pytest

from domain.parsing import parse_bool_it, parse_date_it, parse_decimal_it
from domain.periods import ranges_overlap
from domain.permissions import Permission, Role, has_permission, permissions_for
from domain.recipes import plan_new_version


# --- permessi (SPEC §4) -------------------------------------------------------------
def test_admin_ha_tutti_i_permessi():
    assert permissions_for(Role.ADMIN) == frozenset(Permission)


def test_operatore_legge_ma_non_modifica_anagrafiche():
    assert has_permission(Role.OPERATORE, Permission.MASTERDATA_READ)
    assert not has_permission(Role.OPERATORE, Permission.MASTERDATA_WRITE)
    assert not has_permission(Role.OPERATORE, Permission.USERS_MANAGE)


def test_auditor_legge_anagrafiche_e_audit_ma_non_scrive():
    assert has_permission(Role.AUDITOR, Permission.AUDIT_READ)
    assert not has_permission(Role.AUDITOR, Permission.MASTERDATA_WRITE)
    assert not has_permission(Role.AUDITOR, Permission.IMPORT_RUN)


def test_responsabile_scrive_anagrafiche_ma_non_gestisce_utenti():
    assert has_permission(Role.RESPONSABILE, Permission.MASTERDATA_WRITE)
    assert has_permission(Role.RESPONSABILE, Permission.IMPORT_RUN)
    assert not has_permission(Role.RESPONSABILE, Permission.USERS_MANAGE)


def test_veterinario_sola_lettura():
    assert permissions_for(Role.VETERINARIO) == frozenset({Permission.MASTERDATA_READ})


# --- numeri in formato italiano ----------------------------------------------------
@pytest.mark.parametrize(
    "text,expected",
    [
        ("12,5", Decimal("12.5")),
        ("12.5", Decimal("12.5")),
        ("1.234,56", Decimal("1234.56")),
        ("1,234.56", Decimal("1234.56")),
        (" 7 ", Decimal("7")),
        ("-3,25", Decimal("-3.25")),
    ],
)
def test_parse_decimal_it(text, expected):
    assert parse_decimal_it(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "1,2,3", "NaN", "1.2.3"])
def test_parse_decimal_it_non_valido(text):
    with pytest.raises(ValueError):
        parse_decimal_it(text)


def test_parse_decimal_it_restituisce_decimal_non_float():
    assert isinstance(parse_decimal_it("0,1"), Decimal)
    assert parse_decimal_it("0,1") + parse_decimal_it("0,2") == Decimal("0.3")


@pytest.mark.parametrize(
    "text,expected",
    [("sì", True), ("Si", True), ("1", True), ("x", True), ("no", False), ("", False)],
)
def test_parse_bool_it(text, expected):
    assert parse_bool_it(text) is expected


def test_parse_bool_it_non_valido():
    with pytest.raises(ValueError):
        parse_bool_it("forse")


def test_parse_date_it():
    assert parse_date_it("02/10/2026") == date(2026, 10, 2)
    assert parse_date_it("2026-10-02") == date(2026, 10, 2)
    assert parse_date_it("02-10-2026") == date(2026, 10, 2)
    with pytest.raises(ValueError):
        parse_date_it("31/02/2026")


# --- versionamento ricette (RF-01) -------------------------------------------------
def test_nuova_versione_chiude_la_precedente_il_giorno_prima():
    version, prev_to = plan_new_version(1, date(2026, 1, 1), date(2026, 3, 1))
    assert version == 2
    assert prev_to == date(2026, 2, 28)


def test_nuova_versione_stesso_giorno_e_ammessa():
    version, prev_to = plan_new_version(3, date(2026, 3, 1), date(2026, 3, 1))
    assert version == 4
    assert prev_to == date(2026, 2, 28)


def test_nuova_versione_non_puo_decorrere_prima():
    with pytest.raises(ValueError):
        plan_new_version(1, date(2026, 3, 1), date(2026, 2, 1))


# --- intervalli (occupazioni) ------------------------------------------------------
def test_intervalli_sovrapposti():
    assert ranges_overlap(date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31), None)
    assert ranges_overlap(date(2026, 1, 1), None, date(2026, 6, 1), date(2026, 6, 2))


def test_intervalli_disgiunti():
    assert not ranges_overlap(date(2026, 1, 1), date(2026, 1, 30), date(2026, 1, 31), None)
    assert not ranges_overlap(date(2026, 2, 1), None, date(2026, 1, 1), date(2026, 1, 31))
