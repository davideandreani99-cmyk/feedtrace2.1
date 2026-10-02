import uuid

from tests.api.conftest import API, create_material, create_site


def test_crud_fornitore_e_disattivazione(client, make_account):
    acc = make_account("ADMIN")
    created = client.post(
        f"{API}/suppliers",
        json={"name": "Mangimi Fittizi", "vat_number": "IT00000000009", "medicated_supplier": True},
        headers=acc.headers,
    )
    assert created.status_code == 201
    sid = created.json()["id"]
    assert client.patch(
        f"{API}/suppliers/{sid}", json={"reg_183_number": "REG-1"}, headers=acc.headers
    ).json()["reg_183_number"] == "REG-1"

    deleted = client.delete(f"{API}/suppliers/{sid}", headers=acc.headers).json()
    assert deleted["active"] is False
    # non cancellato: resta consultabile, filtrabile per stato
    assert client.get(f"{API}/suppliers/{sid}", headers=acc.headers).status_code == 200
    active_ids = [s["id"] for s in client.get(
        f"{API}/suppliers", params={"active": True}, headers=acc.headers).json()]
    assert sid not in active_ids


def test_codice_materia_prima_univoco_per_tenant(client, make_account):
    a = make_account("ADMIN")
    b = make_account("ADMIN")
    create_material(client, a, code="MAIS")
    r = client.post(
        f"{API}/raw-materials", json={"code": "MAIS", "name": "x", "type": "CEREALE"},
        headers=a.headers,
    )
    assert r.status_code == 409
    # lo stesso codice in un altro tenant è consentito
    create_material(client, b, code="MAIS")


def test_materia_prima_in_litri_richiede_densita(client, make_account):
    acc = make_account("ADMIN")
    body = {"code": "SIERO", "name": "Siero", "type": "LIQUIDO", "unit": "l"}
    assert client.post(f"{API}/raw-materials", json=body, headers=acc.headers).status_code == 422
    body["density_kg_l"] = "1.025"
    r = client.post(f"{API}/raw-materials", json=body, headers=acc.headers)
    assert r.status_code == 201
    assert r.json()["density_kg_l"] == "1.0250"


def test_percentuale_fuori_range_rifiutata(client, make_account):
    acc = make_account("ADMIN")
    r = client.post(
        f"{API}/raw-materials",
        json={"code": "X", "name": "x", "type": "CEREALE", "dry_matter_pct": "120"},
        headers=acc.headers,
    )
    assert r.status_code == 422


def test_contenitore_politica_default_e_valori_ammessi(client, make_account):
    acc = make_account("ADMIN")
    site = create_site(client, acc)
    r = client.post(
        f"{API}/containers",
        json={"site_id": site["id"], "code": "SILO-1", "type": "SILO", "capacity": "20000"},
        headers=acc.headers,
    )
    assert r.status_code == 201
    assert r.json()["consumption_policy"] == "FIFO"
    assert r.json()["medicated_contaminated"] is False
    bad = client.post(
        f"{API}/containers",
        json={"site_id": site["id"], "code": "SILO-2", "type": "SILO",
              "consumption_policy": "LIFO"},
        headers=acc.headers,
    )
    assert bad.status_code == 422


def test_materiali_ammessi_nel_contenitore(client, make_account):
    acc = make_account("ADMIN")
    site = create_site(client, acc)
    container = client.post(
        f"{API}/containers",
        json={"site_id": site["id"], "code": "SILO-A", "type": "SILO"},
        headers=acc.headers,
    ).json()
    m1, m2 = create_material(client, acc), create_material(client, acc)
    url = f"{API}/containers/{container['id']}/allowed-materials"
    r = client.put(url, json=[m1["id"], m2["id"]], headers=acc.headers)
    assert r.status_code == 200
    assert set(client.get(url, headers=acc.headers).json()) == {m1["id"], m2["id"]}
    client.put(url, json=[m1["id"]], headers=acc.headers)
    assert client.get(url, headers=acc.headers).json() == [m1["id"]]
    assert client.put(url, json=[str(uuid.uuid4())], headers=acc.headers).status_code == 422


def test_operatore_legge_ma_non_scrive_anagrafiche(client, make_account):
    admin = make_account("ADMIN")
    operatore = make_account("OPERATORE", admin.tenant_id)
    assert client.get(f"{API}/suppliers", headers=operatore.headers).status_code == 200
    r = client.post(f"{API}/suppliers", json={"name": "No"}, headers=operatore.headers)
    assert r.status_code == 403


def test_occupazioni_non_si_sovrappongono(client, make_account):
    acc = make_account("ADMIN")
    site = create_site(client, acc)
    loc = client.post(
        f"{API}/locations", json={"site_id": site["id"], "name": "Sala 1"}, headers=acc.headers
    ).json()
    lots = [
        client.post(
            f"{API}/destination-lots",
            json={"site_id": site["id"], "internal_code": f"L{i}", "external_code": f"PIG{i}"},
            headers=acc.headers,
        ).json()
        for i in (1, 2)
    ]
    first = client.post(
        f"{API}/occupancies",
        json={"location_id": loc["id"], "destination_lot_id": lots[0]["id"],
              "date_from": "2026-01-01", "date_to": "2026-03-31"},
        headers=acc.headers,
    )
    assert first.status_code == 201
    overlap = client.post(
        f"{API}/occupancies",
        json={"location_id": loc["id"], "destination_lot_id": lots[1]["id"],
              "date_from": "2026-03-31"},
        headers=acc.headers,
    )
    assert overlap.status_code == 409
    after = client.post(
        f"{API}/occupancies",
        json={"location_id": loc["id"], "destination_lot_id": lots[1]["id"],
              "date_from": "2026-04-01"},
        headers=acc.headers,
    )
    assert after.status_code == 201


# --- ricette versionate (RF-01) ----------------------------------------------------
def _recipe_body(code: str, material_ids: list[str], kg: str = "600", **extra) -> dict:
    return {
        "code": code,
        "name": "Ingrasso base",
        "plant_type": "MISCELATORE_BATCH",
        "phase": "INGRASSO",
        "lines": [{"material_id": m, "kg_per_t": kg} for m in material_ids],
        **extra,
    }


def test_ricetta_nuova_versione_e_storico(client, make_account):
    acc = make_account("ADMIN")
    m1, m2 = create_material(client, acc), create_material(client, acc)
    v1 = client.post(
        f"{API}/recipes",
        json=_recipe_body("R-INGR", [m1["id"], m2["id"]], valid_from="2026-01-01"),
        headers=acc.headers,
    )
    assert v1.status_code == 201, v1.text
    assert v1.json()["version"] == 1 and len(v1.json()["lines"]) == 2

    v2 = client.put(
        f"{API}/recipes/{v1.json()['id']}",
        json=_recipe_body("R-INGR", [m1["id"], m2["id"]], kg="650", valid_from="2026-03-01"),
        headers=acc.headers,
    )
    assert v2.status_code == 200, v2.text
    assert v2.json()["version"] == 2
    assert v2.json()["id"] != v1.json()["id"]

    # la versione 1 resta intatta (righe comprese) e viene chiusa il giorno prima
    old = client.get(f"{API}/recipes/{v1.json()['id']}", headers=acc.headers).json()
    assert old["valid_to"] == "2026-02-28"
    assert old["lines"][0]["kg_per_t"] == "600.000"

    latest = client.get(f"{API}/recipes", headers=acc.headers).json()
    assert [r["version"] for r in latest if r["code"] == "R-INGR"] == [2]
    allv = client.get(
        f"{API}/recipes", params={"all_versions": True, "code": "R-INGR"}, headers=acc.headers
    ).json()
    assert [r["version"] for r in allv] == [1, 2]


def test_ricetta_modifica_solo_ultima_versione(client, make_account):
    acc = make_account("ADMIN")
    m = create_material(client, acc)
    v1 = client.post(
        f"{API}/recipes", json=_recipe_body("R-1", [m["id"]]), headers=acc.headers
    ).json()
    client.put(f"{API}/recipes/{v1['id']}", json=_recipe_body("R-1", [m["id"]]), headers=acc.headers)
    again = client.put(
        f"{API}/recipes/{v1['id']}", json=_recipe_body("R-1", [m["id"]]), headers=acc.headers
    )
    assert again.status_code == 409


def test_ricetta_codice_duplicato_e_righe_non_valide(client, make_account):
    acc = make_account("ADMIN")
    other = make_account("ADMIN")
    m = create_material(client, acc)
    foreign = create_material(client, other)
    assert client.post(
        f"{API}/recipes", json=_recipe_body("R-2", [m["id"]]), headers=acc.headers
    ).status_code == 201
    assert client.post(
        f"{API}/recipes", json=_recipe_body("R-2", [m["id"]]), headers=acc.headers
    ).status_code == 409
    # materia prima ripetuta
    dup = _recipe_body("R-3", [m["id"], m["id"]])
    assert client.post(f"{API}/recipes", json=dup, headers=acc.headers).status_code == 422
    # materia prima di un altro tenant
    r = client.post(
        f"{API}/recipes", json=_recipe_body("R-4", [foreign["id"]]), headers=acc.headers
    )
    assert r.status_code == 422
    # ricetta senza righe
    empty = _recipe_body("R-5", [])
    assert client.post(f"{API}/recipes", json=empty, headers=acc.headers).status_code == 422


def test_ricetta_non_visibile_ad_altro_tenant(client, make_account):
    a = make_account("ADMIN")
    b = make_account("ADMIN")
    m = create_material(client, a)
    r = client.post(f"{API}/recipes", json=_recipe_body("R-A", [m["id"]]), headers=a.headers).json()
    assert client.get(f"{API}/recipes/{r['id']}", headers=b.headers).status_code == 404
    assert client.get(f"{API}/recipes", headers=b.headers).json() == []
