SPEC — Software di tracciabilità dei mangimi per allevamenti suinicoli
Versione 0.1 — bozza da revisionare. Nome provvisorio del prodotto: FeedTrace (da sostituire). Questo documento è la fonte di verità funzionale. In caso di conflitto tra il codice e questa SPEC, vale la SPEC; se la SPEC è ambigua o incompleta, chiedi prima di decidere.


1. Contesto e obiettivo
Gli allevamenti suinicoli italiani che producono mangime in azienda (mulino/miscelatore, impianto a broda, carro miscelatore) o che acquistano mangime finito devono garantire la tracciabilità dei mangimi (Reg. CE 178/2002, Reg. CE 183/2005), gestire i mangimi medicati (Reg. UE 2019/4, Ricetta Elettronica Veterinaria) e, se producono per i circuiti DOP (Prosciutto di Parma / San Daniele), dimostrare la conformità dell'alimentazione al disciplinare.

I gestionali suinicoli esistenti (es. Pig'UP di Isagri) gestiscono bene gli animali ma trattano il mangime solo come consumo/costo; i sistemi d'impianto (Big Dutchman, Schauer, SKOV, ecc.) gestiscono curve e livelli ma non la catena documentale dei lotti.

Obiettivo: un'applicazione web SaaS multi-azienda che gestisca solo il flusso dei mangimi:

Ingresso MATERIE PRIME (lotti)

      └─► CONTENITORI materie prime (silos, tramogge, cisterne, big bag, magazzino)

             └─► PRODUZIONE MISCELE (ricetta → produzione → lotto miscela)

                    └─► CONTENITORI prodotto finito (silos, vasche broda)

                           └─► SCARICHI periodici ─► LOTTI DI DESTINAZIONE (lotti animali)

                                                         └─► API / export ─► gestionale tecnico-economico (es. Pig'UP)

e che permetta in pochi secondi:

tracciabilità all'indietro: da un lotto di destinazione (o da un lotto di miscela) a tutti i lotti di materia prima, fornitori e DDT coinvolti;
tracciabilità in avanti: da un lotto di materia prima (es. un lotto di mais contaminato) a tutte le miscele, contenitori e lotti di destinazione che lo hanno ricevuto.
2. Perimetro
In perimetro (MVP)
Anagrafiche (aziende, siti, fornitori, materie prime, contenitori, impianti, ricette, lotti di destinazione).
Ingresso materie prime e mangimi finiti acquistati, con lotti.
Giacenze per lotto in ogni contenitore, con politica di consumo configurabile per contenitore.
Produzione miscele: miscelatore a batch, broda, carro miscelatore.
Scarichi periodici verso lotti di destinazione (manuali e da import CSV/Excel).
Tracciabilità avanti/indietro e report.
Analisi di laboratorio e quarantena lotti.
Mangimi medicati con riferimento alla REV.
Verifica conformità DOP (ricette e quota annua di origine dalla zona tipica).
Costi (materie prime → miscela → lotto di destinazione).
API REST pubblica documentata + export per gestionali esterni (Pig'UP).
Multi-azienda, utenti e ruoli, audit trail.
Fuori perimetro (non implementare)
Gestione animali (riproduzione, pesi, mortalità, sanità): resta nel gestionale tecnico-economico esterno.
Formulazione nutrizionale / ottimizzazione a costo minimo.
Contabilità, fatturazione, ordini ai fornitori.
Registro elettronico dei trattamenti VetInfo (solo export dati di supporto).
Lettura diretta da PLC/controller (fase 2: per ora solo import file).
Funzionamento offline (fase 2: l'architettura deve però permetterlo, vedi §9).
3. Glossario
Termine
Significato
Tenant / Azienda
Cliente del SaaS (azienda agricola o gruppo). Dati completamente isolati.
Sito
Allevamento/unità produttiva del tenant, con codice aziendale ASL (es. 012PR345).
Materia prima (MP)
Qualsiasi input: cereali, farine, premiscele, integratori, additivi, siero, acqua, mangime finito acquistato, premiscela medicata.
Lotto MP
Partita di MP entrata in un dato momento: lotto fornitore + lotto interno generato.
Contenitore
Luogo fisico che contiene materiale: silo, tramoggia, cisterna, vasca broda, big bag, magazzino a terra.
Impianto
Macchina che produce miscele: miscelatore a batch, impianto broda, carro miscelatore.
Ricetta
Composizione teorica versionata di una miscela.
Produzione
Evento (ciclo/mescolata) in cui un impianto produce una quantità di miscela.
Lotto miscela
Lotto del prodotto realizzato; può raggruppare uno o più cicli (vedi §6.4).
Scarico
Uscita di materiale da un contenitore (o da un impianto broda) verso un lotto di destinazione.
Lotto di destinazione
Gruppo/partita di animali a cui viene imputato il consumo. Corrisponde a un lotto del gestionale esterno (codice Pig'UP).
Movimento
Registrazione elementare immutabile di carico/scarico di quantità di uno specifico lotto in/da un contenitore.
Politica di consumo
Regola con cui un contenitore decide quali lotti escono a ogni scarico (FIFO / PROPORZIONALE / TUTTI_PRESENTI).
4. Utenti e ruoli
Ruolo
Permessi principali
Super admin piattaforma
Gestione tenant, piani, supporto. Non vede i dati operativi salvo impersonificazione esplicita e tracciata.
Amministratore azienda
Tutto sul proprio tenant, utenti e ruoli, configurazioni, chiavi API.
Responsabile mangimificio
Ricette, produzioni, sblocco quarantene, override motivati, inventari.
Operatore
Ingressi, produzioni, scarichi, import file. Nessuna modifica ad anagrafiche critiche.
Veterinario / consulente
Lettura; inserimento REV; registrazione analisi.
Auditor / ente di controllo
Sola lettura + report di tracciabilità, accesso eventualmente a tempo.

Un utente può appartenere a più tenant (es. consulente) e scegliere il tenant attivo.
5. Modello di dominio (entità minime)
Indicativo: Claude Code può proporre nomi/strutture diverse motivandole, ma deve coprire tutti i concetti.

Tenant(id, ragione sociale, P.IVA, piano, impostazioni)
Sito(id, tenant, nome, codice aziendale ASL, indirizzo, provincia, flag circuito DOP)
Fornitore(id, tenant, ragione sociale, P.IVA, n. registrazione/riconoscimento Reg. 183/2005, flag fornitore di mangimi medicati, attivo)
MateriaPrima(id, tenant, codice, nome, tipo [CEREALE, SOTTOPRODOTTO, PROTEICO, PREMISCELA, INTEGRATORE, ADDITIVO, LIQUIDO, ACQUA, MANGIME_FINITO, PREMISCELA_MEDICATA, MANGIME_MEDICATO], unità [kg, l], densità kg/l per liquidi, % sostanza secca, % grassi, % acido linoleico, categoria disciplinare DOP, richiede analisi all'ingresso (bool), tracciata a lotto (bool, false per l'acqua))
LottoMP(id, tenant, materia prima, fornitore, lotto fornitore, codice lotto interno univoco, data ingresso, DDT n./data, targa, quantità iniziale, prezzo €/t, origine [provincia/regione/paese, flag zona tipica DOP], data scadenza, stato [IN_QUARANTENA, DISPONIBILE, NON_CONFORME, BLOCCATO, ESAURITO], allegati)
Contenitore(id, sito, codice, tipo, capacità, unità, materiali ammessi (lista MP o tipi), politica di consumo [FIFO, PROPORZIONALE, TUTTI_PRESENTI], soglia giacenza negativa, flag dedicato medicati, stato contaminazione medicato)
Impianto(id, sito, tipo [MISCELATORE_BATCH, BRODA, CARRO], regola lotto [PER_CICLO, GIORNALIERO_PER_RICETTA], tolleranza scostamento %, costo lavorazione €/t, autorizzato a medicati (bool))
Ricetta(id, tenant, codice, nome, versione, valida da/a, tipo impianto, fase [SVEZZAMENTO, MAGRONAGGIO, INGRASSO, SCROFE, ALTRO], flag DOP, flag medicata) + RigaRicetta(materia prima, quantità per tonnellata o %, contenitore di prelievo predefinito, tolleranza)
Produzione(id, impianto, ricetta+versione, data/ora inizio-fine, quantità teorica, quantità effettiva, operatore, origine dato [MANUALE, IMPORT], lotto miscela) + RigaProduzione(materia prima, contenitore prelievo, q.tà teorica, q.tà effettiva, scostamento %)
LottoMiscela(id, codice, impianto, ricetta, data, quantità totale, stato, flag medicato, riferimento REV)
LottoDestinazione(id, sito, codice interno, codice esterno Pig'UP, descrizione, fase, n. capi (opz.), data inizio/fine, flag DOP, stato [APERTO, CHIUSO])
Luogo(id, sito, capannone/sala/box/valvola) + Occupazione(luogo, lotto destinazione, da, a) — serve a tradurre gli import per valvola/sala in lotti di destinazione.
Movimento (registro immutabile): (id, tenant, data/ora, tipo [CARICO_INGRESSO, PRELIEVO_PRODUZIONE, CARICO_PRODUZIONE, SCARICO_DESTINAZIONE, RETTIFICA_INVENTARIO, SVUOTAMENTO, STORNO], contenitore, lotto (MP o miscela), quantità con segno, riferimento al documento d'origine, utente, id movimento stornato)
LegameTracciabilità: grafo lotto→lotto e lotto→lotto destinazione con quantità attribuita e tipo legame [CERTO, POSSIBILE] (POSSIBILE = presenza per politica TUTTI_PRESENTI).
Analisi(lotto, data prelievo, laboratorio, parametro, valore, unità, limite, esito, allegato)
RicettaVeterinaria (REV)(numero REV, veterinario, data emissione, validità fino a, contiene antimicrobici, principio attivo, dosaggio mg/kg mangime, tempo di attesa giorni, quantità prescritta, lotti di destinazione/categoria animali, allegato)
Pulizia/Svuotamento(contenitore o impianto, data, tipo [SVUOTAMENTO, PULIZIA, FLUSHING], dopo medicato (bool), operatore)
ParametriDisciplinare (versionati, vedi §6.9)
AuditLog(chi, quando, entità, azione, valori prima/dopo, IP)
ApiKey(tenant, nome, scope, scadenza, ultimo uso)
6. Requisiti funzionali
Ogni requisito ha un ID da citare in commit, test e issue.
6.1 Anagrafiche — RF-01
CRUD per tutte le anagrafiche del §5 con validazioni.
Import iniziale da CSV/Excel di: materie prime, fornitori, contenitori, ricette, lotti di destinazione.
Le anagrafiche referenziate da movimenti non si cancellano: si disattivano.
Le ricette si versionano: una modifica crea una nuova versione; le produzioni restano legate alla versione usata.
6.2 Ingresso materie prime — RF-02
Registrazione da DDT: fornitore, data, n. DDT, targa, righe (MP, lotto fornitore, quantità, prezzo, origine, contenitore di destinazione).
Una riga DDT può essere suddivisa su più contenitori.
Il sistema genera il codice lotto interno (formato configurabile, default MP-{AAAA}{MM}{GG}-{progressivo}).
Allegati: foto/PDF di DDT, cartellino, certificato di analisi.
Avvisi bloccanti/non bloccanti:
fornitore senza n. registrazione 183/2005 → avviso (bloccante se configurato);
MP non ammessa nel contenitore scelto → blocco;
capacità contenitore superata → avviso;
MP con "richiede analisi" → lotto creato in stato IN_QUARANTENA.
Materie prime autoprodotte (es. mais aziendale): ingresso senza fornitore esterno, con origine = sito.
Mangime finito acquistato: entra come MP di tipo MANGIME_FINITO direttamente nel silo di prodotto finito e può essere scaricato senza produzione.
6.3 Contenitori e giacenze per lotto — RF-03
Per ogni contenitore: giacenza teorica totale e composizione per lotto (quantità residua per lotto) in tempo reale e a una data passata (ricostruzione dai movimenti).
Politiche di consumo (configurabili per contenitore, modificabili solo a contenitore vuoto o con registrazione in audit):
FIFO: lo scarico consuma i lotti in ordine di ingresso.
PROPORZIONALE: lo scarico consuma ogni lotto in proporzione alla sua quota di giacenza.
TUTTI_PRESENTI: le quantità si scalano in modo proporzionale, ma ai fini della tracciabilità ogni scarico è legato a tutti i lotti mai entrati dall'ultimo svuotamento (legame POSSIBILE) finché non viene registrato uno SVUOTAMENTO o un inventario a zero.
Inventario/rettifica: inserimento giacenza misurata (o letta da sensore, inserita a mano/import); la differenza genera un movimento RETTIFICA_INVENTARIO ripartito secondo la politica del contenitore; la rettifica richiede motivazione.
Svuotamento/pulizia: azzera la composizione (le quantità residue diventano rettifica) e chiude la catena dei legami POSSIBILE.
Giacenza negativa: consentita con avviso e segnalazione nel cruscotto "anomalie" (dati di impianto spesso arrivano in ritardo); non deve bloccare l'import.
Visualizzazione: elenco contenitori con barra di riempimento, lotti presenti, stato contaminazione medicato, stato quarantena.
6.4 Produzione miscele — RF-04
Tre modalità con la stessa struttura dati (Produzione + righe):
MISCELATORE_BATCH: una mescolata = una produzione; destinazione = contenitore prodotto finito.
CARRO: come batch; destinazione = direttamente uno o più lotti di destinazione (scarico contestuale) o un contenitore.
BRODA: molti cicli al giorno; destinazione = vasca/serbatoio o direttamente scarichi a valvole/lotti di destinazione; ingredienti liquidi (siero) in litri convertiti in kg con densità; l'acqua è ingrediente non tracciato a lotto.
Regola lotto miscela configurabile per impianto:
PER_CICLO: ogni produzione genera un nuovo lotto miscela;
GIORNALIERO_PER_RICETTA: tutte le produzioni dello stesso impianto, stessa ricetta e stesso giorno confluiscono nello stesso lotto miscela (codice es. MX-{impianto}-{AAAAMMGG}-{ricetta}).
Per ogni riga: quantità teorica (da ricetta × quantità prodotta) e quantità effettiva; il prelievo dei lotti dal contenitore di prelievo segue la politica di quel contenitore e genera i legami di tracciabilità lotto MP → lotto miscela.
Controlli:
scostamento riga oltre tolleranza → avviso registrato sulla produzione;
uso di lotto IN_QUARANTENA / NON_CONFORME / BLOCCATO → blocco; override consentito solo al Responsabile con motivazione obbligatoria (in audit);
ricetta medicata senza REV valida collegata → blocco (vedi RF-08);
impianto/contenitore contaminato da medicato e ricetta non medicata → avviso bloccante finché non si registra pulizia/flushing (configurabile).
Inserimento manuale rapido (da tablet in stalla) e import file (RF-06).
6.5 Scarichi verso lotti di destinazione — RF-05
Scarico = contenitore (o produzione broda/carro) → lotto di destinazione, con data o periodo (da–a) e quantità.
Uso tipico: registrazione periodica (giornaliera/settimanale) delle quantità per lotto, oppure import dai report dell'impianto.
Se l'origine dato è per luogo (valvola/sala/capannone), il sistema risolve il lotto di destinazione tramite la tabella Occupazione; se il luogo non è occupato nel periodo → riga in errore da risolvere a mano.
Lo scarico consuma i lotti del contenitore secondo la sua politica e crea i legami lotto miscela/MP → lotto destinazione.
Lotto destinazione CHIUSO → nessun nuovo scarico (salvo riapertura con motivazione).
Riepilogo per lotto di destinazione: kg totali per ricetta/fase/periodo, costo, lotti miscela e MP coinvolti, presenza di medicati e data di fine tempo di attesa.
6.6 Import file — RF-06
Import CSV/XLSX per: ingressi, produzioni, scarichi, inventari.
Mappature salvabili per formato (es. "Export broda impianto X"): corrispondenza colonne, formato date, separatore decimale, codici esterni ↔ anagrafiche (codici ricetta, valvole, silos).
Flusso: carica file → anteprima con validazione riga per riga → conferma → movimenti generati in un'unica transazione; riepilogo righe ok/scartate scaricabile.
Idempotenza: un file (hash) o una riga (chiave naturale configurabile) già importati non vengono duplicati.
Le righe importate restano collegate al file d'origine (consultabile).
6.7 Tracciabilità — RF-07
Indietro da: lotto destinazione, lotto miscela, contenitore a una data. Risultato: albero/grafo fino ai lotti MP, con fornitore, DDT, quantità attribuite, analisi e stato, distinguendo legami CERTI e POSSIBILI.
Avanti da: lotto MP, lotto miscela, fornitore + periodo. Risultato: miscele, contenitori, lotti di destinazione raggiunti, quantità stimate, date, codici Pig'UP.
Vista grafica (grafo/albero) + tabella + export PDF ("Scheda di tracciabilità") ed Excel.
Prestazioni: risposta < 2 s su 3 anni di dati di un sito medio (≈ 200.000 movimenti).
Simulazione richiamo: da un lotto MP, elenco lotti di destinazione coinvolti con quantità e contatti, in un'unica schermata stampabile.
6.8 Analisi e quarantena — RF-08
Registrazione analisi su lotti MP o lotti miscela (es. aflatossina B1, DON, zearalenone, fumonisine, umidità, proteina), con limiti configurabili per MP/parametro.
Stati del lotto e transizioni: IN_QUARANTENA → DISPONIBILE (esito conforme, approvato dal Responsabile) / NON_CONFORME; DISPONIBILE ↔ BLOCCATO (blocco manuale motivato).
Blocco d'uso in produzione/scarico come in RF-04; esito NON_CONFORME su un lotto già usato → avviso con link alla tracciabilità in avanti.
6.9 Mangimi medicati e REV — RF-09
Registrazione REV (dati §5) collegata a: produzione di miscela medicata oppure ingresso di mangime medicato acquistato, e ai lotti di destinazione autorizzati.
Controlli: REV scaduta (validità ~21 giorni; ridotta per antimicrobici — valori di default configurabili, da verificare con la normativa vigente), quantità prescritta superata, lotto destinazione non incluso → blocco.
Impianto non autorizzato ai medicati → blocco produzione medicata.
Dopo produzione/stoccaggio medicato, impianto e contenitore passano a stato "contaminato medicato" fino a registrazione di pulizia/flushing.
Tempo di attesa: per ogni lotto di destinazione, data di fine = data ultimo scarico medicato + giorni di attesa; esposta in UI, report e API.
Export di supporto alla registrazione nel Registro elettronico dei trattamenti (CSV con dati del trattamento); nessuna integrazione diretta VetInfo nell'MVP.
6.10 Conformità DOP — RF-10
Tabella ParametriDisciplinare versionata per disciplinare (default: Prosciutto di Parma, versione 2025), modificabile dall'admin piattaforma; seed con i valori sotto, marcati "da verificare sul testo ufficiale":
fasi: svezzamento (≤ 40 kg, nessun vincolo specifico), magronaggio (≤ 85 kg), ingrasso;
limiti % sulla sostanza secca della razione per categoria (es. mais ≤ 65%, orzo/frumento/sorgo/triticale ≤ 55%, cereali minori ≤ 25%, farina glutinata mais ≤ 10%, cruscami ≤ 20%, pastone di granella di mais ≤ 55%, soia ≤ 20%, girasole ≤ 10%, colza ≤ 10%, melasso ≤ 5%, erba medica ≤ 4%, piselli/leguminose ≤ 25%, lieviti ≤ 2%, farina di pesce ≤ 1% e vietata in ingrasso, soia integrale tostata vietata in ingrasso);
siero ≤ 15 l/capo/giorno; latticello ≤ 250 g/capo/giorno;
sostanza secca da cereali ≥ 45% (magronaggio), ≥ 55% (ingrasso);
acido linoleico ≤ 2% della s.s.; grassi ≤ 5% della s.s.;
≥ 50% della s.s. annua da zona tipica.
Verifica ricetta: per ricette con flag DOP e fase, calcolo sulla s.s. e semaforo per ogni vincolo; blocco del salvataggio come "ricetta DOP" se non conforme (salvabile come non-DOP).
Verifica produzione/scarico: scarico di miscela non conforme su lotto destinazione DOP → avviso bloccante configurabile.
Report annuale origine: per sito DOP e anno solare, s.s. totale somministrata ai lotti DOP e quota da zona tipica, con dettaglio per MP e lotti; semaforo ≥ 50%.
Siero/latticello per capo/giorno calcolato se il lotto destinazione ha n. capi.
6.11 Costi — RF-11
Prezzo per lotto MP (€/t da DDT, modificabile fino a chiusura periodo).
Costo lotto miscela = Σ (quantità effettive × prezzo lotti consumati) + costo lavorazione impianto €/t.
Costo scarico = quantità × costo medio del materiale consumato (secondo i lotti effettivamente consumati).
Report: costo per lotto destinazione, per periodo, per ricetta; €/t medio per ricetta nel tempo.
Chiusura periodo (mensile): blocca modifiche a prezzi e movimenti del periodo; correzioni solo tramite storno nel periodo aperto.
6.12 Report — RF-12
Registro di carico/scarico mangimi e materie prime (per sito, periodo) stampabile per ASL / ente di controllo.
Scheda di tracciabilità (RF-07), report quarantene/analisi, report medicati e tempi di attesa, report DOP annuale, costi.
Cruscotto: giacenze per contenitore, lotti in quarantena, contenitori contaminati, REV in scadenza, anomalie (giacenze negative, scostamenti, righe import in errore).
Tutti i report: PDF + XLSX, con intestazione azienda/sito, data di generazione, utente.
6.13 API ed export — RF-13
API REST JSON versionata (/api/v1), specifica OpenAPI 3 generata e pubblicata, autenticazione con API key per tenant con scope (lettura/scrittura per risorsa) + OAuth2 client credentials (opzionale fase 2).
Risorse minime: materie prime, lotti MP, contenitori e giacenze, ricette, produzioni, lotti miscela, lotti destinazione, scarichi, consumi aggregati per lotto destinazione e periodo (kg, ricetta, fase, costo, flag medicato, fine tempo di attesa), tracciabilità avanti/indietro.
Paginazione, filtri per data di modifica (updated_since) per sincronizzazioni incrementali, idempotency key sulle scritture.
Connettore gestionali esterni come interfaccia astratta (ExternalFarmSystemAdapter) con una prima implementazione "Pig'UP – export CSV" (formato da definire, vedi §11); l'implementazione via API Pig'UP verrà aggiunta quando Isagri fornirà la documentazione.
Webhook (fase 2): eventi lot.non_compliant, withdrawal.ending, import.completed.
6.14 Audit e integrità — RF-14
I movimenti sono immutabili: correzioni solo tramite STORNO + nuovo movimento.
Audit log di ogni creazione/modifica/cancellazione logica su qualunque entità, con valori prima/dopo.
Override di blocchi sempre con motivazione, utente e timestamp, evidenziati nei report.
7. Regole di calcolo da testare esplicitamente (casi d'esempio)
I test automatici devono coprire almeno questi scenari (con numeri):

FIFO: silo con lotto A 10 t (entrato prima) e B 5 t; scarico 12 t → A 0, B 3 t; legami: 10 t da A, 2 t da B.
PROPORZIONALE: stesso silo; scarico 6 t → A −4 t, B −2 t.
TUTTI_PRESENTI: silo con A, poi carico B, scarico, poi carico C, scarico: il secondo scarico è legato (POSSIBILE) ad A, B, C; dopo SVUOTAMENTO + carico D, il successivo scarico è legato solo a D.
Lotto giornaliero per ricetta: 3 cicli broda della ricetta R1 lo stesso giorno + 1 ciclo di R2 → 2 lotti miscela.
Quarantena: lotto in quarantena usato in produzione → errore; override del Responsabile → produzione registrata con flag e audit.
Medicato: produzione medicata con REV scaduta → errore; con REV valida → contenitore contaminato; produzione non medicata successiva nello stesso impianto senza flushing → blocco.
Tempo di attesa: ultimo scarico medicato 10/03, attesa 5 gg → fine 15/03.
DOP: ricetta ingrasso con mais 70% s.s. → non conforme; con farina di pesce → non conforme in ingrasso.
Origine annua: 60 t s.s. zona tipica su 100 t → 60% conforme.
Costo: miscela con 600 kg di lotto mais a 250 €/t + 400 kg di lotto soia a 450 €/t + lavorazione 10 €/t → 340 €/t.
Import idempotente: stesso file importato due volte → nessun duplicato.
Ricostruzione storica: giacenza per lotto di un contenitore a una data passata = somma movimenti fino a quella data.
8. Interfaccia utente
Lingua: italiano (predisposta i18n). Formati: date gg/mm/aaaa, separatore decimale virgola, fuso Europe/Rome, unità kg/t/l.
Responsive: usabile da PC in ufficio e da tablet/telefono in stalla (pulsanti grandi per le operazioni rapide: ingresso, produzione, scarico, inventario).
Codici QR stampabili per contenitori e lotti: la scansione apre la scheda/operazione rapida.
Navigazione principale: Cruscotto · Ingressi · Contenitori · Produzione · Scarichi · Lotti destinazione · Tracciabilità · Qualità (analisi/quarantene) · Medicati · DOP · Costi · Report · Anagrafiche · Impostazioni.
Accessibilità: contrasto adeguato, uso con guanti/schermi piccoli (target touch ≥ 44 px).
9. Requisiti non funzionali
Multi-tenant con isolamento forte (tenant_id su tutte le tabelle + Row Level Security o equivalente), test che dimostrano l'impossibilità di accesso cross-tenant.
Database relazionale PostgreSQL (transazioni, query ricorsive per il grafo di tracciabilità).
Quantità con precisione decimale (mai float): kg con 3 decimali.
Offline-ready (fase 2): le operazioni rapide devono essere progettate come comandi idempotenti con id generato dal client, per permettere in futuro una coda offline.
Sicurezza: autenticazione con email+password e 2FA opzionale, password hash robusto, rate limiting, OWASP Top 10, segreti fuori dal codice.
GDPR: dati personali minimi (utenti, veterinari), export/cancellazione utenti, registro trattamenti.
Backup giornaliero e procedura di ripristino documentata; conservazione dati ≥ 5 anni.
Osservabilità: log strutturati, health check, tracciamento errori.
Qualità: test unitari sulle regole di dominio (copertura ≥ 90% del modulo dominio), test d'integrazione API, test E2E dei flussi principali; lint e type-check in CI.
Deploy: Docker / docker-compose per sviluppo; pronto per un hosting cloud europeo.
10. Dati demo (seed)
Generare un tenant fittizio realistico, "Azienda Agricola Demo – Cascina Esempio" (nessun riferimento a aziende reali), con:

2 siti (uno in circuito DOP), 8 fornitori fittizi con n. registrazione inventato in formato plausibile;
~20 materie prime (mais, orzo, frumento tenero, crusca, farina estrazione soia, girasole, siero, premiscela vitaminico-minerale, lisina, carbonato di calcio, mangime prestarter acquistato, premiscela medicata, acqua…);
1 miscelatore a batch (PER_CICLO), 1 impianto broda (GIORNALIERO_PER_RICETTA), 1 carro; 14 contenitori con politiche diverse;
6 ricette (svezzamento, magronaggio DOP, ingrasso DOP, ingrasso non DOP, scrofe, ingrasso medicato) di cui una volutamente non conforme DOP;
10 lotti di destinazione con codice Pig'UP fittizio e occupazioni dei luoghi;
4 mesi di movimenti coerenti (ingressi settimanali, produzioni giornaliere, scarichi), 1 lotto di mais con aflatossine non conforme già usato (per demo richiamo), 1 REV e un ciclo medicato con tempo di attesa, 2 file CSV d'esempio da importare (broda e scarichi).
11. Domande aperte (da chiudere prima o durante lo sviluppo)
Formato codici lotto (interni, miscela) definitivo e se stamparli su etichette.
API Pig'UP: cosa espone Isagri, autenticazione, possibilità di scrivere i consumi per lotto. Fino ad allora: formato CSV di export da concordare.
Formati reali degli export degli impianti (broda, miscelatori, pese) dei primi clienti.
Durate di validità REV e regole medicati: verificare testo vigente (Reg. UE 2019/4, D.Lgs. di attuazione, note ministeriali).
Disciplinare DOP: verifica puntuale dei parametri sul testo ufficiale; aggiungere San Daniele e altri.
Modello di prezzo SaaS (per sito, per tonnellata, per utente) → impatta su piani e limiti nel tenant.
Nome prodotto e branding.
