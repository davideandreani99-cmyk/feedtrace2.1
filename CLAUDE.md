CLAUDE.md — Regole di lavoro per questo repository
Il progetto
Applicazione web SaaS multi-azienda per la tracciabilità dei mangimi negli allevamenti suinicoli: materie prime a lotti → contenitori → produzione miscele → scarichi verso lotti di destinazione (lotti animali del gestionale esterno, es. Pig'UP). La specifica completa è in docs/SPEC.md: leggila per intero prima di ogni fase e cita gli ID dei requisiti (RF-xx) in commit, test e PR.
Principi non negoziabili
Il dominio prima della UI. Le regole (politiche di consumo dei silos, legami di tracciabilità, quarantena, medicati, DOP, costi) vivono in un modulo di dominio puro, senza dipendenze da framework o DB, coperto da test unitari (≥ 90%).
Movimenti immutabili. Nessun UPDATE/DELETE sui movimenti: si corregge con STORNO + nuovo movimento. Ogni modifica ad altre entità va nell'audit log.
Mai float per le quantità o i prezzi. Usa tipi decimali (DB numeric, librerie decimali nel codice).
Isolamento tenant ovunque. Ogni query è filtrata per tenant; aggiungi test che tentano accessi cross-tenant e devono fallire.
API-first. Ogni funzione della UI passa da API documentate in OpenAPI; la UI non ha accesso diretto privilegiato.
Operazioni idempotenti per ingressi, produzioni, scarichi e import (id generato dal client / chiave di idempotenza): servirà per l'offline in fase 2.
Niente dati reali. Seed e test usano solo dati fittizi; nessun nome di aziende, persone o codici reali.
Modo di lavorare
Lavora per fasi (vedi docs/PIANO.md, che creerai in Fase 0). Alla fine di ogni fase: test verdi, lint/type-check puliti, breve nota in docs/CHANGELOG.md, poi fermati e chiedi la revisione prima della fase successiva.
Se un requisito è ambiguo o in conflitto, non inventare: elenca le opzioni con pro/contro e chiedi. Le scelte prese vanno registrate in docs/DECISIONI.md (formato ADR breve: contesto, decisione, conseguenze).
Commit piccoli e descrittivi in italiano, con riferimento ai requisiti (es. RF-03: politica PROPORZIONALE e test).
Scrivi i test dei casi del §7 della SPEC prima dell'implementazione delle relative regole.
Non aggiungere funzionalità fuori perimetro (§2 della SPEC) senza chiedere.
Mantieni aggiornati: README.md (avvio locale in ≤ 5 comandi), specifica OpenAPI, docs/DECISIONI.md.
Convenzioni
Lingua: codice e identificatori in inglese; UI, messaggi d'errore per l'utente, documentazione e commit in italiano. Il glossario di dominio (SPEC §3) definisce la traduzione dei termini: usala in modo coerente (es. Contenitore = Container, Lotto di destinazione = DestinationLot, Scarico = Discharge, Politica di consumo = ConsumptionPolicy).
Date in UTC nel DB, mostrate in Europe/Rome; formati italiani in UI.
Unità: kg nel DB; conversioni (t, l con densità) solo ai bordi.
Comandi
Stack: Python 3.12 + FastAPI + SQLAlchemy/Alembic + PostgreSQL; React + TypeScript + Vite. Ambiente: GitHub Codespaces (.devcontainer).
- Migrazioni: `cd backend && alembic upgrade head`
- Seed fittizio: `python -m app.cli seed-dev`
- API: `uvicorn app.main:app --reload --host 0.0.0.0` (docs su /api/docs)
- Frontend: `cd frontend && npm run dev`
- Test: `cd backend && pytest` (dominio: `pytest tests/domain --cov=domain --cov-fail-under=90`)
- Lint/tipi: `ruff check . && mypy domain` (backend; `mypy app` informativo fino a F2), `npm run build` (frontend)
