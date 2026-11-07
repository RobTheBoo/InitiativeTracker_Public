# RPG Initiative Tracker (Windows)

Repository pubblico per il download dell'installer Windows.

## Download

- Ultima versione: [Scarica da GitHub Releases](https://github.com/RobTheBoo/InitiativeTracker_Public/releases/latest)

## Catalogo dati

- Manifest v1: [catalogo legacy](https://raw.githubusercontent.com/RobTheBoo/InitiativeTracker_Public/main/catalog/v1/manifest.json)
- Manifest v2: [catalogo con distribuzione incorporata](https://raw.githubusercontent.com/RobTheBoo/InitiativeTracker_Public/main/catalog/v2/manifest.json)
- Struttura e validazione: [documentazione catalogo](./catalog/v1/README.md)

Il catalogo v1 mantiene il fixture originale di prova. Il manifest v2.20.0 contiene 63 pacchetti: i 61 pacchetti Pathfinder 1e già presenti e due pacchetti separati di condizioni D&D verificati sui soli PDF ufficiali Wizards SRD 5.1 (2014) e SRD 5.2.1 (2024). I pacchetti D&D contengono rispettivamente 14 e 15 definizioni di condizioni, con licenza CC BY 4.0, attribuzione ufficiale, versione, checksum del PDF e pagina fonte; sono estratti limitati, non cataloghi completi degli SRD. La condizione Petrified del pacchetto 2014 è esclusa perché l'estrazione della pagina sorgente non era affidabile. Non sono stati importati database comunitari o contenuti D&D ulteriori.

I 61 pacchetti Pathfinder 1e contengono 287 incantesimi, 34 condizioni, 6.112 effetti, 1.795 blocchi statistici di creature e PNG e 3.429 oggetti. La selezione non-spell copre le voci indicizzate nei database dello snapshot i cui titoli compaiono nell'avviso Section 15 incorporato, inclusi Advanced Race Guide, Game Mastery Guide, NPC Codex e Ultimate Campaign; non tratta come redistribuibile una fonte solo perché presente nel database. L'audit nominativo registra inoltre 194 effetti, 97 creature e 286 oggetti ancora trattenuti per attribuzioni di terzi, PI da verificare, duplicati identici, contenuti corrotti/incompleti o fonti non coperte (fra cui Technology Guide). Le eccezioni sono tracciate per record, fonte e sezione nella coda e nell'audit; un record trattenuto non è una determinazione di non-redistribuibilità. I blocchi delle creature contengono solo statistiche strutturate, gli oggetti solo fatti tabellari e gli effetti solo testo di regole, senza artwork. Ogni asset v2 incorpora licenza OGL 1.0a, avvisi Section 15 e mappatura delle fonti per ciascun elemento. `redistributionStatus: "verified"` è un'attestazione del publisher, non una garanzia legale né una revisione legale indipendente.

L'identificatore ruleset `PTFD` (edizione `1e`) è usato per compatibilità tecnica. I pacchetti non sono affiliati, sponsorizzati né approvati da titolari di marchi o diritti.

## Installazione

1. Apri la pagina di download.
2. Scarica il file `.exe` della versione piu recente.
3. Avvia l'installer e segui la procedura guidata.

## Note

- Questo repository non contiene il codice sorgente del progetto.
- Qui vengono pubblicati l'installer Windows e il catalogo dati dell'applicazione.

## Privacy

- Informativa privacy: [PRIVACY-POLICY.md](./PRIVACY-POLICY.md)

## Problemi / Supporto

Se il download non parte o l'installer non si avvia, apri una issue in questo repository con:

- versione scaricata
- versione di Windows
- messaggio di errore (se presente)
