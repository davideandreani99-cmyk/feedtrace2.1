# Fase 0 — Analisi: dominio, stack, architettura, modello dati

Riferimento: `docs/SPEC.md` v0.1. Nessun codice applicativo scritto.

## 1. Comprensione del dominio

1. **Flusso**: ingresso MP (lotto MP) → contenitori (giacenza *per lotto*) → produzione (ricetta versionata × quantità) → lotto miscela → contenitore prodotto finito o scarico diretto (broda/carro) → scarichi periodici verso lotti di destinazione (codice Pig'UP). Il mangime finito acquistato entra come MP e può essere scaricato senza produzione.
2. **Il Movimento è l'unica fonte di verità**: registro append-only con quantità con segno. Giacenze, composizione per lotto e ricostruzione a data passata sono *derivate* (somma dei movimenti fino alla data). Nessun UPDATE/DELETE: correzione = STORNO + nuovo movimento.
3. **Politica di consumo (per contenitore)** decide *quali lotti* escono a ogni uscita (prelievo produzione, scarico, svuotamento, rettifica): **FIFO** (ordine di ingresso, un lotto si esaurisce prima del successivo), **PROPORZIONALE** (ogni lotto cala in proporzione alla quota), **TUTTI_PRESENTI** (quantità scalate in proporzione, ma ai fini di tracciabilità l'uscita è legata a *tutti* i lotti entrati dall'ultimo svuotamento).
4. **Legami**: ogni prelievo genera archi lotto→lotto (MP→miscela) e lotto→lotto destinazione con quantità attribuita. **CERTO** = consumo effettivo (FIFO/PROPORZIONALE); **POSSIBILE** = sola presenza (TUTTI_PRESENTI). La catena POSSIBILE si chiude con SVUOTAMENTO o inventario a zero.
5. **Lotto miscela per impianto**: PER_CICLO (un lotto per produzione) o GIORNALIERO_PER_RICETTA (stesso impianto + stessa ricetta + stesso giorno → stesso lotto, tipico della broda). Va risolto *idempotentemente* (get-or-create) e il lotto accumula quantità e legami.
6. **Tracciabilità** all'indietro (destinazione/miscela/contenitore a data → MP, fornitori, DDT) e in avanti (MP/miscela/fornitore+periodo → destinazioni), < 2 s su ~200k movimenti, distinguendo CERTI/POSSIBILI. Per composizione di miscele in cascata (MP→miscela→silo→destinazione) le quantità si propagano per quote.
7. **Blocchi e override**: lotti IN_QUARANTENA/NON_CONFORME/BLOCCATO non utilizzabili; override solo del Responsabile con motivazione, sempre in audit e evidenziato nei report.
8. **Medicati**: REV valida (scadenza, quantità, lotti destinazione ammessi), impianto autorizzato, contaminazione di impianto/contenitore fino a pulizia/flushing, tempo di attesa = ultimo scarico medicato + giorni.
9. **DOP**: verifica ricetta sulla sostanza secca (semaforo per vincolo) e report annuo di origine (≥ 50% s.s. da zona tipica) per sito DOP.
10. **Costi**: costo lotto miscela = Σ(kg effettivi × prezzo lotto) + lavorazione €/t; costo scarico = kg × costo medio dei lotti *effettivamente* consumati; chiusura periodo mensile blocca prezzi e movimenti.
11. **Vincoli trasversali**: decimali (kg a 3 decimali), kg nel DB, UTC nel DB / Europe/Rome in UI, tenant isolato (RLS), operazioni idempotenti con id client, giacenza negativa ammessa con anomalia (non blocca gli import).

### Punti ambigui, contraddittori o mancanti nella SPEC

| # | Punto | Problema |
|---|---|---|
| A1 | §6.3 TUTTI_PRESENTI | La quantità attribuita ai legami POSSIBILE non è definita (zero? proporzionale alla giacenza? pari all'intero scarico per ciascun lotto?). Incide su richiamo e costi. |
| A2 | §6.3 TUTTI_PRESENTI | "lotti mai entrati dall'ultimo svuotamento" include i lotti già esauriti: confermare (il test §7 lo suggerisce). |
| A3 | §6.3/§7 FIFO | "ordine di ingresso": data di ingresso del lotto MP o del carico *nel contenitore*? Spareggio a parità di timestamp? Un lotto in più contenitori ha ordini diversi per contenitore. |
| A4 | §6.3 | Arrotondamento a 3 decimali nel PROPORZIONALE: dove va il resto (lotto maggiore? ultimo?). Serve regola deterministica. |
| A5 | Manca | **Trasferimenti tra contenitori (travaso)** e uscite non verso destinazione (vendita/reso MP, scarto, smaltimento scaduti): non c'è un tipo di movimento. Proposta: TRASFERIMENTO (coppia di movimenti) e SCARTO/USCITA_ALTRO. |
| A6 | §6.3 giacenza negativa | Prelievo da un contenitore senza lotti sufficienti: a quale lotto si attribuisce l'eccedenza? Proposta: lotto sintetico "NON ALLOCATO" per contenitore, riallocato dall'inventario/dai carichi tardivi. |
| A7 | §6.3/§9 dati in ritardo | Movimenti retrodatati: la ricostruzione storica cambia i risultati di FIFO/legami già calcolati. Servono: ricalcolo dei legami da una data (come storno+riemissione) oppure divieto di retrodatazione oltre una soglia. |
| A8 | §6.4 | GIORNALIERO_PER_RICETTA: "stessa ricetta" = stessa *versione*? Se la ricetta cambia versione a metà giornata? Giorno calcolato in Europe/Rome? |
| A9 | §6.4 BRODA | Scarico diretto a valvole senza contenitore intermedio: da dove vengono i movimenti di carico/scarico del lotto miscela? Proposta: CARICO_PRODUZIONE e SCARICO_DESTINAZIONE sull'impianto come contenitore virtuale. |
| A10 | §6.4 CARRO | "Scarico contestuale": confermare che genera produzione + scarico in un'unica operazione atomica con più lotti destinazione e ripartizione quantità. |
| A11 | §6.4 acqua/liquidi | Acqua non tracciata ma conta nella s.s. e nei litri broda; densità per liquido costante o variabile per lotto? |
| A12 | §5 vs §6.9 | `ParametriDisciplinare` rimandato a "§6.9" ma è il §6.10. REV: §6.8 cita "RF-08" per i medicati, ma sono RF-09. |
| A13 | §6.10 DOP | I limiti % sono su "s.s. della razione"; la verifica ricetta usa la ricetta (miscela), non la razione complessiva (può includere altri alimenti/siero). Chiarire il perimetro. Categorie sovrapposte (mais ≤65% vs "cereali"?). Siero 15 l/capo/die richiede n. capi (opzionale in §5). |
| A14 | §6.10 | "Vietata in ingrasso" per soia integrale tostata/farina di pesce: valori "da verificare"; limiti e fasi per peso (≤40, ≤85 kg) richiedono un criterio di passaggio fase sul lotto (peso non gestito qui). |
| A15 | §6.9 REV | Quantità prescritta in kg di mangime o di principio attivo? Una REV per più lotti destinazione e più produzioni (consumo cumulato)? Chi può inserirla: §4 dice Veterinario "lettura; inserimento REV" — confermare. |
| A16 | §6.11 | Prezzo modificabile "fino a chiusura periodo": ricalcolo a cascata dei costi derivati (miscele e scarichi) oppure calcolo a lettura? Storno in periodo chiuso: data del movimento di storno nel periodo aperto ma stornato nel chiuso. |
| A17 | §6.11 | Costo con lotti POSSIBILI: costo medio su quali lotti (solo CERTI?) |
| A18 | §6.2 | Lotto interno formato configurabile: progressivo per tenant/giorno/sito? Concorrenza. |
| A19 | §4 | Super admin "senza dati operativi salvo impersonificazione tracciata": implica bypass RLS controllato; definire il meccanismo. Utente multi-tenant: identità globale vs ruolo per tenant. |
| A20 | §6.7 | Prestazioni "su un sito medio": con catene lunghe e legami POSSIBILI il grafo può esplodere; serve un limite di profondità/pruning dichiarato. |
| A21 | §6.1/§6.6 | Livello di concorrenza sullo stesso contenitore (due operatori scaricano insieme): serve serializzazione per contenitore. |
| A22 | §2/§6.2 | Mangime medicato acquistato e premiscela medicata: contaminazione dell'impianto quando la premiscela è usata solo come MP in una ricetta (flag medicata della ricetta vs MP). |

## 2. Proposta di stack

**Raccomandazione: Python 3.12 + FastAPI + SQLAlchemy 2 / Alembic + PostgreSQL 16 · React + TypeScript + Vite (SPA responsive, PWA-ready) · Docker.**

| Area | Scelta | Motivazione |
|---|---|---|
| Backend | FastAPI (Pydantic v2) | OpenAPI 3 generata dal codice, tipi forti, idempotency/dependency injection semplici. |
| Dominio puro | Pacchetto `domain/` Python senza import di framework/DB, `decimal.Decimal` | Test unitari veloci (pytest + hypothesis), ≥ 90%. Decimal nativo, niente float. |
| DB/ORM | PostgreSQL + SQLAlchemy 2 + Alembic | RLS (`SET LOCAL app.tenant_id`), CTE ricorsive, `numeric(18,3)`, constraint, trigger anti UPDATE/DELETE sui movimenti. |
| Job | Dramatiq (o arq) + Redis | Import file, report pesanti; semplice per un team piccolo. |
| PDF / XLSX | WeasyPrint (HTML→PDF), openpyxl/XlsxWriter | Report con intestazione e template HTML condivisibili. |
| Frontend | React + TS + Vite, TanStack Query, client generato da OpenAPI (openapi-typescript), UI kit con target touch ≥ 44 px | UI senza accesso privilegiato; service worker/PWA aggiungibile in fase 2. Grafi: Cytoscape/React Flow. |
| Auth | Argon2id, sessioni/JWT breve + refresh, TOTP opzionale; API key hashed con scope | Come §9. |
| Test | pytest, testcontainers-postgres, Playwright (E2E), ruff + mypy strict, eslint + tsc | CI GitHub Actions. |
| Deploy | Docker multi-stage + docker-compose (api, worker, db, redis, web); target: cloud UE (Scaleway/Hetzner/OVH/AWS eu) | Nessun lock-in. |

**Alternative scartate**
- *NestJS + Prisma/TypeORM (TypeScript full-stack)*: un solo linguaggio e OpenAPI decente, ma RLS e decimali meno ergonomici (Prisma non supporta bene RLS per-transazione), librerie PDF/XLSX meno solide per report stampabili.
- *Django + DRF*: scelta matura e valida (admin, auth, ORM); scartata come primaria perché ORM e framework tendono a infiltrarsi nel dominio, OpenAPI via drf-spectacular meno precisa; resta l'alternativa se si preferisce "batterie incluse".
- *.NET / Java Spring*: ottimi ma team/ecosistema più pesante per un team piccolo.
- *Event sourcing con event store dedicato*: eccessivo; il registro Movimenti su PostgreSQL basta.
- *Database per tenant*: isolamento massimo ma costo operativo alto; si adotta RLS su schema condiviso (con possibilità di DB dedicato per grandi clienti).

## 3. Architettura

### Moduli (bounded context)
`identity` (utenti, tenant, ruoli, API key, audit) · `masterdata` (siti, fornitori, MP, contenitori, impianti, ricette, lotti destinazione, luoghi/occupazioni) · `inventory` (ingressi, movimenti, giacenze, inventari, svuotamenti) · `production` (produzioni, lotti miscela) · `discharge` (scarichi, import) · `traceability` (grafo, query, richiamo) · `quality` (analisi, quarantena) · `medicated` (REV, contaminazione, tempi attesa) · `compliance_dop` · `costing` (costi, chiusura periodo) · `reporting` (PDF/XLSX, cruscotto) · `integration` (API pubblica, `ExternalFarmSystemAdapter`, Pig'UP CSV).

### Dominio puro
`backend/domain/` contiene: politiche di consumo (funzioni pure: `(lotti_in_contenitore, quantità) → allocazioni + legami`), regola lotto miscela, macchina a stati dei lotti, regole REV/tempo di attesa, verifica DOP, calcolo costi, conversioni unità. Nessun I/O. Gli *application service* (nel modulo) caricano lo stato, invocano il dominio, persistono movimenti/legami in una transazione.

### Grafo di tracciabilità (< 2 s su ~200k movimenti)
- Fonte: tabella `traceability_link(from_lot, to_lot, quantity, kind, movement_id, tenant_id)` popolata **in scrittura** nella stessa transazione del movimento (legami precomputati, archi lotto→lotto e lotto→destinazione).
- Query: CTE ricorsive `WITH RECURSIVE` su indici `(tenant_id, to_lot)` e `(tenant_id, from_lot)`, con limite di profondità (tipicamente ≤ 5 livelli: MP→miscela→(miscela)→destinazione) e protezione da cicli (array dei percorsi / `CYCLE`).
- Quote: la quantità attribuita si propaga per frazioni lungo il percorso; per legami POSSIBILI quantità nulla o "peso" (vedi A1).
- Se serve: tabella materializzata `lot_closure` (antenato/discendente, quantità, tipo) aggiornata incrementalmente per lotto destinazione; benchmark in F5 con seed da 200k movimenti prima di decidere.
- Giacenze: tabella `container_lot_balance` (aggiornata con i movimenti, con lock per contenitore) + ricostruzione storica da `movement` con indice `(tenant_id, container_id, occurred_at)`.

### Multi-tenant
`tenant_id` su ogni tabella; **RLS** con policy `tenant_id = current_setting('app.tenant_id')::uuid`; il ruolo applicativo non è proprietario (niente `BYPASSRLS`); la connessione imposta il tenant per transazione (`SET LOCAL`). Super admin: ruolo DB distinto, accessi ai dati operativi solo via impersonificazione scritta in audit. Test cross-tenant obbligatori (API + DB diretto).

### Autenticazione e API key
Utenti globali con appartenenza `(user, tenant, ruolo)`; tenant attivo nel token. API key: prefisso + segreto (hash SHA-256/Argon2), scope `risorsa:read|write`, scadenza, `last_used_at`, rate limit. Permessi per ruolo (§4) in un unico modulo di policy, usato da UI e API.

### Import e idempotenza
Ogni scrittura accetta `Idempotency-Key`/id client (UUID) con vincolo `UNIQUE(tenant_id, idempotency_key)` su ingressi, produzioni, scarichi. Import: tabella `import_file` (hash SHA-256 unico per tenant), `import_row` con chiave naturale configurabile e stato; flusso upload → anteprima (validazione) → conferma → job che genera i movimenti in una transazione; risultato scaricabile. Un secondo import dello stesso hash o stessa riga naturale è no-op.

## 4. Modello dati

Convenzioni: `id uuid`, `tenant_id` ovunque, `numeric(18,3)` per kg, `numeric(18,4)` per prezzi, timestamp `timestamptz` UTC, `created_at/by`, disattivazione logica (`active`), audit via trigger/servizio.

```mermaid
erDiagram
  TENANT ||--o{ SITE : has
  TENANT ||--o{ USER_MEMBERSHIP : has
  USER ||--o{ USER_MEMBERSHIP : belongs
  TENANT ||--o{ API_KEY : has
  SITE ||--o{ CONTAINER : has
  SITE ||--o{ PLANT : has
  SITE ||--o{ LOCATION : has
  SITE ||--o{ DESTINATION_LOT : has
  LOCATION ||--o{ OCCUPANCY : has
  DESTINATION_LOT ||--o{ OCCUPANCY : in
  SUPPLIER ||--o{ RAW_MATERIAL_LOT : supplies
  RAW_MATERIAL ||--o{ RAW_MATERIAL_LOT : of
  RAW_MATERIAL_LOT ||--o{ MOVEMENT : moved
  RECIPE ||--o{ RECIPE_LINE : has
  RAW_MATERIAL ||--o{ RECIPE_LINE : used_in
  PLANT ||--o{ PRODUCTION : runs
  RECIPE ||--o{ PRODUCTION : uses
  PRODUCTION ||--o{ PRODUCTION_LINE : has
  PRODUCTION }o--|| FEED_MIX_LOT : yields
  CONTAINER ||--o{ MOVEMENT : holds
  FEED_MIX_LOT ||--o{ MOVEMENT : moved
  MOVEMENT ||--o| MOVEMENT : reverses
  DISCHARGE ||--o{ MOVEMENT : generates
  DESTINATION_LOT ||--o{ DISCHARGE : receives
  MOVEMENT ||--o{ TRACE_LINK : produces
  TRACE_LINK }o--|| DESTINATION_LOT : to
  RAW_MATERIAL_LOT ||--o{ ANALYSIS : tested
  FEED_MIX_LOT ||--o{ ANALYSIS : tested
  VET_PRESCRIPTION ||--o{ FEED_MIX_LOT : covers
  VET_PRESCRIPTION ||--o{ VET_PRESCRIPTION_DEST : allows
  DESTINATION_LOT ||--o{ VET_PRESCRIPTION_DEST : allowed
  CONTAINER ||--o{ CLEANING : cleaned
  PLANT ||--o{ CLEANING : cleaned
  IMPORT_FILE ||--o{ IMPORT_ROW : contains
  ACCOUNTING_PERIOD ||--o{ MOVEMENT : closes
```

### Tabelle principali (chiavi e vincoli)

| Tabella | Chiavi / vincoli chiave |
|---|---|
| `tenant` | PK id; `vat_number` unico. |
| `app_user`, `membership(user_id, tenant_id, role)` | UNIQUE(user_id, tenant_id); 2FA opzionale. |
| `site` | UNIQUE(tenant_id, asl_code); `dop_circuit bool`. |
| `supplier` | UNIQUE(tenant_id, vat_number); `reg_183_number`, `medicated_supplier`. |
| `raw_material` | UNIQUE(tenant_id, code); `type` enum, `unit` (kg\|l), `density_kg_l` (CHECK obbligatoria se l), `dry_matter_pct`, `fat_pct`, `linoleic_pct`, `dop_category`, `requires_analysis`, `lot_tracked`. |
| `raw_material_lot` | UNIQUE(tenant_id, internal_code); FK material, supplier (null se autoprodotta), `status` enum, `price_eur_t`, `origin_*`, `typical_zone bool`, `initial_qty`. |
| `container` | UNIQUE(site_id, code); `consumption_policy` enum, `negative_threshold_kg`, `medicated_only`, `medicated_contaminated`; tabella `container_allowed_material`. |
| `plant` | `type`, `lot_rule`, `tolerance_pct`, `processing_cost_eur_t`, `medicated_authorized`, `medicated_contaminated`. |
| `recipe`, `recipe_line` | UNIQUE(tenant_id, code, version); validità `daterange` con EXCLUDE per non sovrapposizione; righe immutabili per versione. |
| `production`, `production_line` | UNIQUE(tenant_id, idempotency_key); FK recipe version; `override_reason`, `source` (MANUAL\|IMPORT), `import_row_id`. |
| `feed_mix_lot` | UNIQUE(tenant_id, code); per GIORNALIERO: UNIQUE(plant_id, recipe_id, lot_date). |
| `destination_lot` | UNIQUE(tenant_id, internal_code); `external_code` (Pig'UP) indice; `status`. |
| `location`, `occupancy` | EXCLUDE (location, `daterange`) per evitare sovrapposizioni. |
| `movement` | **append-only** (trigger `BEFORE UPDATE OR DELETE` → errore); `type` enum, `container_id`, `lot_kind/lot_id`, `quantity numeric(18,3)` con segno, `source_doc_type/id`, `reverses_movement_id` UNIQUE (uno storno per movimento), `idempotency_key`, `period_id`; indici `(tenant_id, container_id, occurred_at)`, `(tenant_id, lot_id)`. |
| `container_lot_balance` | PK(container_id, lot_id); CHECK in-app (giacenza negativa ammessa); `entered_seq` per FIFO; `since_emptying_epoch` per TUTTI_PRESENTI. |
| `discharge` | `from_container_id` o `from_production_id`, `destination_lot_id`, `period_from/to`, UNIQUE idempotency. |
| `trace_link` | `(from_lot, to_lot_or_dest, quantity, kind CERTO\|POSSIBILE, movement_id)`; indici su entrambe le direzioni. |
| `analysis`, `lot_status_history` | storico transizioni con utente/motivo. |
| `vet_prescription` (+`_dest`) | `valid_until`, `prescribed_qty`, `withdrawal_days`, `antimicrobial`. |
| `cleaning` | `type`, `after_medicated`, azzera la contaminazione e chiude la catena POSSIBILE (epoca). |
| `dop_parameter` | `(disciplinare, version, category, phase, limit_type, value, verified bool)` — non per tenant (globale). |
| `accounting_period` | UNIQUE(tenant_id, year, month), `closed_at`. |
| `import_mapping`, `import_file`, `import_row` | UNIQUE(tenant_id, file_hash); UNIQUE(tenant_id, mapping, natural_key). |
| `audit_log` | append-only; `entity, entity_id, action, before jsonb, after jsonb, user, ip`. |
| `api_key` | `key_hash`, `prefix`, `scopes[]`, `expires_at`, `last_used_at`. |
