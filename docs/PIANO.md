# Piano a fasi

Analisi, stack e modello dati: `docs/ANALISI.md`. Decisioni e domande: `docs/DECISIONI.md`.
Regola comune a tutte le fasi (CLAUDE.md): test dei casi §7 scritti **prima** delle regole; a fine fase test verdi, lint/type-check puliti, nota in `docs/CHANGELOG.md`, stop e richiesta di revisione.

Adattamenti rispetto alla traccia: (1) **F2 anticipa la tabella dei legami e la giacenza per lotto** solo per i movimenti di ingresso/svuotamento, ma le tre politiche sono implementate come dominio puro già in F2 (sono usate da F3 e F4); (2) la **chiusura periodo** è modellata già in F1 (colonna `period_id`) per non migrare i movimenti dopo; (3) **benchmark di performance** del grafo anticipato a fine F4 con seed da 200k movimenti, per decidere la materializzazione prima di F5.

---

## F1 — Fondamenta (RF-01, RF-14)
- **Obiettivo**: scheletro eseguibile e sicuro, anagrafiche complete.
- **Requisiti**: RF-01, RF-14, §4 ruoli, §9 (tenant, RLS, sicurezza base).
- **Deliverable**: monorepo (`backend/`, `frontend/`, `docker-compose`), CI, auth (email+password, TOTP opzionale), tenant + membership + ruoli, RLS, audit log, CRUD anagrafiche con disattivazione e versioning ricette, import iniziale CSV/XLSX anagrafiche, OpenAPI pubblicata, README ≤ 5 comandi, comandi in CLAUDE.md.
- **Test**: unit sui permessi per ruolo; integrazione API; **cross-tenant (API e SQL diretto) devono fallire**; versioning ricetta (la produzione resta legata alla versione); trigger anti UPDATE/DELETE su `audit_log`.
- **Accettazione**: avvio locale in ≤ 5 comandi; un utente di tenant A non legge/scrive nulla del tenant B; ogni modifica ha riga di audit con before/after.
- **Rischi**: configurazione RLS con pool di connessioni (mitigazione: `SET LOCAL` per transazione + test); scelta framework UI.

## F2 — Ingressi MP, contenitori e giacenze per lotto (RF-02, RF-03)
- **Obiettivo**: movimenti immutabili e giacenza per lotto con le tre politiche.
- **Requisiti**: RF-02, RF-03, §9 idempotenza.
- **Deliverable**: dominio puro `consumption_policy` (FIFO/PROPORZIONALE/TUTTI_PRESENTI), registro `movement` con trigger append-only e STORNO, ingresso da DDT (split su più contenitori, codice lotto interno configurabile, allegati, avvisi/blocchi, quarantena automatica), giacenza e composizione in tempo reale e a data passata, inventario/rettifica, svuotamento/pulizia, giacenza negativa con anomalia, UI ingressi/contenitori.
- **Test (§7)**: FIFO (A 10 t, B 5 t, scarico 12 t → A 0, B 3, legami 10/2); PROPORZIONALE (scarico 6 t → A −4, B −2); TUTTI_PRESENTI (sequenza A,B,C + SVUOTAMENTO + D); ricostruzione storica a data passata; idempotenza ingresso; property-based: somma delle allocazioni = quantità scaricata, mai float.
- **Accettazione**: tutti i casi §7 relativi verdi; nessun UPDATE/DELETE possibile sui movimenti (anche da SQL); copertura dominio ≥ 90%.
- **Rischi**: ambiguità A1–A7 (vanno chiuse con te prima di iniziare); concorrenza sullo stesso contenitore (lock per contenitore).

## F3 — Ricette versionate e produzione miscele (RF-04)
- **Obiettivo**: produzione nelle tre modalità con legami MP→miscela.
- **Requisiti**: RF-04.
- **Deliverable**: dominio regola lotto (PER_CICLO / GIORNALIERO_PER_RICETTA, get-or-create idempotente), produzione batch/carro/broda (conversione litri→kg per densità, acqua non tracciata), righe teoriche vs effettive, scostamenti, blocchi lotto IN_QUARANTENA/NON_CONFORME/BLOCCATO con override Responsabile motivato, blocco ricetta medicata senza REV (aggancio a F6) e contaminazione, UI inserimento rapido tablet.
- **Test (§7)**: lotto giornaliero (3 cicli R1 + 1 R2 → 2 lotti); quarantena (errore e override con flag+audit); scostamento > tolleranza → avviso; conversione litri; idempotenza produzione.
- **Accettazione**: i legami MP→miscela corrispondono alla politica del contenitore di prelievo; ogni override evidenziato in audit.
- **Rischi**: A8–A11 (confini del giorno, versione ricetta, broda diretta); flusso carro con scarico contestuale.

## F4 — Lotti di destinazione, occupazioni, scarichi, import (RF-05, RF-06)
- **Obiettivo**: chiudere il flusso fino al lotto animale e importare da file.
- **Requisiti**: RF-05, RF-06.
- **Deliverable**: lotti destinazione e luoghi/occupazioni, scarichi (data o periodo), risoluzione luogo→lotto, blocco lotto CHIUSO (riapertura motivata), riepilogo per lotto, import CSV/XLSX con mappature salvabili, anteprima riga per riga, conferma transazionale, job in background, idempotenza per file (hash) e riga (chiave naturale), tracciamento del file d'origine, report righe ok/scartate. **Benchmark** con seed da 200k movimenti.
- **Test (§7)**: import idempotente (stesso file due volte → zero duplicati); luogo non occupato → riga in errore; scarico su lotto chiuso; giacenza negativa non blocca l'import; test integrazione import con file d'esempio broda/scarichi.
- **Accettazione**: file importato → movimenti generati in un'unica transazione; riepilogo scaricabile; benchmark documentato.
- **Rischi**: formati reali di impianto non noti (domanda aperta §11.3); righe parziali.

## F5 — Tracciabilità, richiamo, report, cruscotto (RF-07, RF-12)
- **Obiettivo**: risposta < 2 s su 200k movimenti.
- **Requisiti**: RF-07, RF-12.
- **Deliverable**: query avanti/indietro (CTE ricorsive, eventuale `lot_closure` in base al benchmark), distinzione CERTO/POSSIBILE, vista grafo/albero + tabella, simulazione richiamo stampabile, Scheda di tracciabilità PDF/XLSX, registro carico/scarico, cruscotto (giacenze, anomalie), QR code per contenitori/lotti.
- **Test**: indietro da destinazione; avanti da lotto MP contaminato; performance < 2 s su dataset 200k (test automatico con soglia); profondità/cicli; golden file dei PDF.
- **Accettazione**: tempi misurati in CI; report con intestazione azienda/sito/data/utente.
- **Rischi**: esplosione di legami POSSIBILI (A20); qualità del PDF.

## F6 — Analisi/quarantena, medicati e REV, DOP, costi (RF-08…RF-11)
- **Obiettivo**: regole di conformità e costo.
- **Requisiti**: RF-08, RF-09, RF-10, RF-11.
- **Deliverable**: analisi con limiti e transizioni di stato, avviso su lotto già usato con link alla tracciabilità in avanti; REV con controlli, contaminazione impianto/contenitore, pulizia/flushing, tempo di attesa; `dop_parameter` versionati (marcati "da verificare"), verifica ricetta con semaforo, report annuale origine; costi miscela/scarico, chiusura periodo mensile.
- **Test (§7)**: medicato con REV scaduta → errore; REV valida → contenitore contaminato; produzione non medicata senza flushing → blocco; tempo di attesa 10/03 + 5 gg = 15/03; DOP mais 70% non conforme, farina di pesce in ingrasso non conforme; origine 60/100 t = 60%; costo 600 kg×250 + 400 kg×450 + 10 €/t = 340 €/t; periodo chiuso blocca modifiche.
- **Accettazione**: tutti i casi §7 rimanenti verdi; parametri DOP e durate REV configurabili e non hardcoded.
- **Rischi**: valori normativi da verificare (§11.4–5); ricalcolo costi su variazione prezzo (A16).

## F7 — API pubblica, adattatore Pig'UP, hardening, seed demo (RF-13, §9, §10)
- **Obiettivo**: prodotto consegnabile.
- **Requisiti**: RF-13, §9, §10.
- **Deliverable**: API `/api/v1` completa con paginazione, `updated_since`, idempotency key, API key con scope, rate limit; `ExternalFarmSystemAdapter` + export CSV Pig'UP (formato da concordare); hardening OWASP, GDPR (export/cancellazione utente), backup + procedura di ripristino, osservabilità (log JSON, health, error tracking); seed demo completo come da §10 con 2 CSV d'esempio; E2E dei flussi principali.
- **Test**: contract test OpenAPI; scope per API key; rate limiting; E2E (ingresso → produzione → scarico → richiamo); restore del backup.
- **Accettazione**: seed demo avviabile e navigabile; scenario richiamo del mais con aflatossine dimostrabile; checklist sicurezza completata.
- **Rischi**: formato/API Pig'UP non ancora forniti (§11.2); copertura E2E.
