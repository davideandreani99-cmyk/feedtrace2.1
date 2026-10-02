# Changelog

## Fase 1 — Fondamenta (RF-01, RF-14, §4, §9) — in revisione

**Stato di verifica: il codice NON è ancora stato eseguito.** Sul PC di sviluppo non erano
installati Python/Node/PostgreSQL; test, lint e type-check vanno eseguiti la prima volta nel
Codespace (vedi README). Eventuali errori emersi vengono corretti prima dell'approvazione.

Aggiunto:
- Progetto: backend FastAPI + PostgreSQL, frontend React/TS, ambiente Codespaces, CI, Docker.
- Dominio puro (`backend/domain`): ruoli/permessi (§4), parsing numeri/date italiani,
  versionamento ricette, sovrapposizione intervalli, enumerazioni.
- Multi-tenant: `tenant_id` su ogni tabella, Row Level Security forzata, ruolo DB applicativo
  non proprietario; controllo dei riferimenti (FK) per tenant.
- Autenticazione: Argon2id, JWT, TOTP opzionale, blocco dopo troppi tentativi, cambio tenant,
  gestione utenti del tenant (ruoli ADMIN, RESPONSABILE, OPERATORE, VETERINARIO, AUDITOR).
- Audit log immutabile (trigger + privilegi) con valori prima/dopo.
- Anagrafiche con disattivazione logica: siti, fornitori, materie prime, contenitori (+ materiali
  ammessi), impianti, lotti di destinazione, luoghi e occupazioni (senza sovrapposizioni).
- Ricette versionate (nuova versione a ogni modifica, storico intatto).
- Import CSV/XLSX con anteprima e conferma (fornitori, materie prime, contenitori, lotti
  destinazione, ricette).
- Tabella `accounting_period` predisposta per la chiusura periodo (F6).

Decisioni di implementazione da confermare:
- Migrazione iniziale basata sui modelli (`create_all`); dalle prossime fasi migrazioni esplicite.
- Token JWT in `Authorization: Bearer` (nessun cookie → nessun CSRF); conservato in localStorage.
- Tabella `app_user` globale senza RLS (serve per il login); l'API non la espone fuori tenant.
  Valutare RLS dedicata in F7 (hardening).
- Rate limiting dei login in memoria (un solo processo); versione robusta in F7.
- Cambio della politica di consumo di un contenitore: oggi solo tracciato in audit; il vincolo
  "solo a contenitore vuoto" arriva in F2 con le giacenze.
- Editor grafico delle ricette e gestione utenti da interfaccia rimandati: disponibili via API/import.
- Client TypeScript generato dalla specifica OpenAPI rimandato a F7 (oggi chiamate manuali).
