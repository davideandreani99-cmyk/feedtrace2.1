# Decisioni (ADR brevi)

## Decisioni confermate dal committente (2026-10-02)

| # | Tema | Decisione |
|---|---|---|
| D1 | Ambiente | Sviluppo e prove online (es. GitHub Codespaces + hosting UE), nessuna installazione sul PC del committente. |
| D2 | Stack | Python + FastAPI + PostgreSQL, React + TypeScript. |
| D3 | FIFO | Ordine per data di carico nel contenitore; a parità, ordine di registrazione. |
| D4 | TUTTI_PRESENTI | Legami POSSIBILE con quantità proporzionale alla giacenza; includono i lotti esauriti dall'ultimo svuotamento. |
| D5 | Arrotondamento | Il resto dei 3 decimali nel PROPORZIONALE va al lotto con la quota maggiore. |
| D6 | Movimenti extra | Aggiunti TRASFERIMENTO tra contenitori e USCITA_ALTRO (vendita/reso/scarto). |
| D7 | Giacenza negativa | Eccedenza su lotto sintetico "NON ALLOCATO", riallocato da carichi/inventari. |
| D8 | Date passate | Libere entro 7 giorni (con ricalcolo legami); oltre solo il Responsabile con motivazione. |
| D9 | Lotto giornaliero | Un lotto per impianto + ricetta + **versione** + giorno (Europe/Rome). |
| D10 | Scarico diretto | L'impianto è contenitore virtuale (carico produzione + scarico destinazione); il carro può ripartire su più lotti. |
| D11 | DOP | Verifica sulla ricetta della miscela; valori "da verificare", configurabili. |
| D12 | REV | Quantità in kg di mangime; inseribile da Veterinario e Responsabile; validità default 21 gg configurabile. |
| D13 | Costi | Calcolati a lettura (si aggiornano al variare dei prezzi fino alla chiusura periodo); solo legami CERTI. |
| D14 | Codici lotto | `MP-{AAAA}{MM}{GG}-{progressivo}` e `MX-{impianto}-{AAAAMMGG}-{ricetta}`; progressivo per sito; etichette QR in F5. |
| D15 | Login | Email+password, TOTP opzionale; SMTP configurabile da variabili d'ambiente. |
| D16 | Dati reali | Nessuno disponibile: formati CSV d'esempio inventati e CSV Pig'UP da concordare. |
| D17 | Default tecnici (decisi dall'assistente) | Monorepo; GitHub Actions; hosting UE da scegliere in F7; nome provvisorio "FeedTrace"; super admin da riga di comando; tenant con `plan` + `settings` JSON; conservazione ≥ 5 anni anche per audit e allegati; allegati max 10 MB. |

Le domande seguenti sono quindi chiuse; restano come storico.

Stato ADR-001…004: **ACCETTATE** con le scelte sopra.

## ADR-001 — Stack
- **Contesto**: web responsive (PWA futura), PostgreSQL, OpenAPI da codice, multi-tenant forte, PDF/XLSX, job, team piccolo, Docker su cloud UE.
- **Decisione (proposta)**: Python 3.12 + FastAPI + SQLAlchemy 2/Alembic + PostgreSQL 16; React + TypeScript + Vite; Dramatiq + Redis; WeasyPrint + openpyxl; Docker.
- **Conseguenze**: Decimal nativo e dominio puro semplice da testare; RLS via `SET LOCAL`; due linguaggi (Python/TS) con client TS generato da OpenAPI. Alternative (NestJS/Prisma, Django, .NET) in `docs/ANALISI.md` §2.

## ADR-002 — Movimenti append-only con legami precomputati
- **Contesto**: tracciabilità < 2 s su ~200k movimenti, immutabilità.
- **Decisione (proposta)**: `movement` append-only (trigger DB), `trace_link` scritta nella stessa transazione, CTE ricorsive; materializzazione (`lot_closure`) solo se il benchmark di F4 lo richiede.
- **Conseguenze**: scritture un po' più costose, letture veloci; ricalcolo legami per retrodatazioni = storno + riemissione.

## ADR-003 — Multi-tenant con RLS su schema condiviso
- **Decisione (proposta)**: `tenant_id` ovunque + RLS, ruolo applicativo senza `BYPASSRLS`, test cross-tenant. Super admin con impersonificazione tracciata.
- **Conseguenze**: costo operativo basso; DB dedicato per grandi clienti rimane possibile.

## ADR-004 — Dominio puro
- **Decisione**: `backend/domain/` senza dipendenze da framework/DB/IO; copertura ≥ 90%.

---

## Domande per te (da chiudere prima della F1, quelle marcate ★ bloccano la F2)

**Stack e organizzazione**
1. Confermi lo stack proposto (Python/FastAPI + React/TS) o preferisci TypeScript full-stack / Django?
2. Monorepo unico con `backend/` e `frontend/`? Quale hosting UE di riferimento (es. Scaleway, Hetzner, OVH, AWS eu) e quale CI (GitHub Actions?)?
3. Nome prodotto e branding (usiamo "FeedTrace" come nome provvisorio nel codice?).
4. Autenticazione: sessione con cookie o token JWT? 2FA TOTP in F1 o più avanti? Hai un provider email (SMTP) per reset password/inviti?
5. Super admin: serve un pannello dedicato già in F1 o solo da riga di comando?

**Regole di dominio**
6. ★ TUTTI_PRESENTI: quanta quantità attribuiamo ai legami POSSIBILE (zero / pesata sulla giacenza / intera)? Includiamo i lotti già esauriti dall'ultimo svuotamento? (A1, A2)
7. ★ FIFO: ordine per data di ingresso del lotto MP o di carico nel contenitore? Spareggio a parità di data? (A3)
8. ★ Arrotondamento a 3 decimali nel PROPORZIONALE: resto al lotto con maggiore quota? (A4)
9. ★ Aggiungiamo i movimenti **TRASFERIMENTO** tra contenitori e **USCITA_ALTRO** (vendita/reso/scarto)? Sono fuori dalla lista della SPEC ma servono davvero. (A5)
10. ★ Giacenza negativa: eccedenza attribuita a un lotto sintetico "NON ALLOCATO" riallocato poi da carichi/inventari? (A6)
11. Movimenti retrodatati: li consentiamo con ricalcolo (storno + riemissione dei legami) o vietiamo oltre N giorni? (A7)
12. Lotto giornaliero: "stessa ricetta" = stessa versione? Il giorno è in Europe/Rome? (A8)
13. Broda e carro con scarico diretto: confermi che l'impianto si comporta come contenitore virtuale (carico produzione + scarico destinazione)? (A9, A10)
14. DOP: i limiti si applicano alla ricetta/miscela o alla razione complessiva (con siero, ecc.)? Hai accesso al testo ufficiale del disciplinare per verificare i valori? (A13, A14)
15. REV: quantità prescritta in kg di mangime o di principio attivo? Chi può inserirla (Veterinario sì, Responsabile?)? Valori di validità REV da usare come default? (A15)
16. Costi: la variazione di un prezzo ricalcola i costi di miscele e scarichi già esistenti (calcolo a lettura) o no? Costo medio su legami POSSIBILI: includerli? (A16, A17)
17. Formato dei codici lotto interni e miscela: confermi `MP-{AAAA}{MM}{GG}-{progressivo}` e `MX-{impianto}-{AAAAMMGG}-{ricetta}`; progressivo per tenant o per sito? Etichette da stampare? (A18)

**Integrazioni e dati**
18. Hai esempi reali (anche anonimizzati) di export di impianto broda/miscelatore/pese per progettare le mappature in F4?
19. Pig'UP: documentazione API già disponibile? In caso contrario, definiamo ora un formato CSV di export dei consumi per lotto (campi e separatori)?
20. Limiti e priorità: quali piani/limiti SaaS (per sito/tonnellata/utente) devo prevedere nel modello tenant (campo `plan` + `settings` JSON sufficiente per ora)?
21. Retention: conservazione dati ≥ 5 anni confermata anche per audit log e allegati? Dimensione massima allegati?

Dopo le tue risposte aggiorno questo file (ADR definitivi) e parto dalla F1.
