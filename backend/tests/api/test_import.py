import io

from openpyxl import Workbook

from tests.api.conftest import API, create_material, create_site


def _post(client, acc, entity, content: bytes, filename="dati.csv", confirm=False):
    return client.post(
        f"{API}/imports/{entity}",
        params={"confirm": confirm},
        files={"file": (filename, content, "application/octet-stream")},
        headers=acc.headers,
    )


def test_import_fornitori_anteprima_e_conferma(client, make_account):
    acc = make_account("ADMIN")
    csv_data = (
        "name;vat_number;medicated_supplier\n"
        "Fornitore Uno;IT00000000101;sì\n"
        "Fornitore Due;IT00000000102;no\n"
    ).encode()
    preview = _post(client, acc, "suppliers", csv_data).json()
    assert preview["ok"] == 2 and preview["errors"] == [] and preview["applied"] is False
    assert client.get(f"{API}/suppliers", headers=acc.headers).json() == []

    done = _post(client, acc, "suppliers", csv_data, confirm=True).json()
    assert done["applied"] is True
    names = {s["name"]: s for s in client.get(f"{API}/suppliers", headers=acc.headers).json()}
    assert names["Fornitore Uno"]["medicated_supplier"] is True
    assert names["Fornitore Due"]["medicated_supplier"] is False


def test_import_idempotente_stesso_file_due_volte_nessun_duplicato(client, make_account):
    acc = make_account("ADMIN")
    csv_data = b"code;name;type\nMAIS;Mais;CEREALE\nORZO;Orzo;CEREALE\n"
    assert _post(client, acc, "raw-materials", csv_data, confirm=True).json()["applied"] is True
    second = _post(client, acc, "raw-materials", csv_data, confirm=True).json()
    assert second["applied"] is False
    assert len(second["errors"]) == 2
    assert len(client.get(f"{API}/raw-materials", headers=acc.headers).json()) == 2


def test_import_numeri_italiani_e_materie_in_litri(client, make_account):
    acc = make_account("ADMIN")
    csv_data = (
        "code;name;type;unit;density_kg_l;dry_matter_pct\n"
        "SIERO;Siero di latte;LIQUIDO;l;1,025;6,5\n"
        "MAIS;Mais;cereale;kg;;86,25\n"
    ).encode()
    assert _post(client, acc, "raw-materials", csv_data, confirm=True).json()["applied"] is True
    items = {m["code"]: m for m in client.get(f"{API}/raw-materials", headers=acc.headers).json()}
    assert items["SIERO"]["density_kg_l"] == "1.0250"
    assert items["SIERO"]["dry_matter_pct"] == "6.500"
    assert items["MAIS"]["type"] == "CEREALE"
    assert items["MAIS"]["dry_matter_pct"] == "86.250"


def test_import_con_errori_non_applica_nulla(client, make_account):
    acc = make_account("ADMIN")
    csv_data = b"code;name;type\nOK1;Valida;CEREALE\nKO1;Tipo errato;INESISTENTE\nOK1;Doppia;CEREALE\n"
    result = _post(client, acc, "raw-materials", csv_data, confirm=True).json()
    assert result["applied"] is False
    assert result["ok"] == 1
    assert {e["line"] for e in result["errors"]} == {3, 4}
    assert client.get(f"{API}/raw-materials", headers=acc.headers).json() == []


def test_import_contenitori_con_codice_sito(client, make_account):
    acc = make_account("ADMIN")
    site = create_site(client, acc, asl_code="012PR345")
    csv_data = (
        "site_code;code;type;capacity;consumption_policy\n"
        "012PR345;SILO-1;SILO;20.000,5;PROPORZIONALE\n"
        "999XX999;SILO-2;SILO;100;FIFO\n"
    ).encode()
    result = _post(client, acc, "containers", csv_data, confirm=True).json()
    assert result["applied"] is False and len(result["errors"]) == 1
    ok = b"site_code;code;type;capacity;consumption_policy\n012PR345;SILO-1;SILO;20.000,5;PROPORZIONALE\n"
    assert _post(client, acc, "containers", ok, confirm=True).json()["applied"] is True
    container = client.get(f"{API}/containers", headers=acc.headers).json()[0]
    assert container["site_id"] == site["id"]
    assert container["capacity"] == "20000.500"
    assert container["consumption_policy"] == "PROPORZIONALE"


def test_import_xlsx(client, make_account):
    acc = make_account("ADMIN")
    wb = Workbook()
    ws = wb.active
    ws.append(["name", "vat_number"])
    ws.append(["Fornitore Excel", "IT00000000555"])
    buffer = io.BytesIO()
    wb.save(buffer)
    result = _post(client, acc, "suppliers", buffer.getvalue(), "fornitori.xlsx", True).json()
    assert result["applied"] is True
    assert client.get(f"{API}/suppliers", headers=acc.headers).json()[0]["name"] == "Fornitore Excel"


def test_import_ricette_formato_lungo(client, make_account):
    acc = make_account("ADMIN")
    create_material(client, acc, code="MAIS")
    create_material(client, acc, code="SOIA")
    csv_data = (
        "recipe_code;recipe_name;plant_type;phase;material_code;kg_per_t\n"
        "R-ING;Ingrasso;MISCELATORE_BATCH;INGRASSO;MAIS;650,5\n"
        "R-ING;Ingrasso;MISCELATORE_BATCH;INGRASSO;SOIA;349,5\n"
    ).encode()
    result = _post(client, acc, "recipes", csv_data, confirm=True).json()
    assert result["applied"] is True, result
    recipe = client.get(f"{API}/recipes", headers=acc.headers).json()[0]
    assert recipe["code"] == "R-ING" and recipe["version"] == 1
    assert [line["kg_per_t"] for line in recipe["lines"]] == ["650.500", "349.500"]


def test_import_operatore_non_autorizzato_e_entita_sconosciuta(client, make_account):
    admin = make_account("ADMIN")
    operatore = make_account("OPERATORE", admin.tenant_id)
    assert _post(client, operatore, "suppliers", b"name\nX\n").status_code == 403
    assert _post(client, admin, "animali", b"a\n1\n").status_code == 404
    assert _post(client, admin, "suppliers", b"x", "dati.txt").status_code == 422
