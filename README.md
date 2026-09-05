# AVATEG

AVATEG è un framework di pipeline automatizzata per rilevare, isolare e classificare anomalie di gameplay in video di videogiochi, con un approccio ibrido che combina:

- ricerca e routing di video su YouTube;
- clipping automatico basato su commenti, compilations e showcases;
- rilevamento visivo di freeze tramite OpenCV;
- diagnosi semantica di clip sospette tramite analisi visiva e descrizione contestuale.

L'obiettivo è trasformare un video grezzo in un set di segnalazioni temporali e report di anomalie verificabili, pronti per essere revisionati e validati manualmente.

---

## Obiettivo del progetto

Il progetto analizza contenuti video di gameplay, individuando anomalie da:

- commenti pubblici di YouTube (NLP/heuristics);
- scene visive di compilation;
- rilevamento di immagini ferme o movimenti anomali;
- analisi semantica di clip sospette tramite revisione contestuale.

Il risultato finale è un pipeline che produce report strutturati e clip isolate per supportare la verifica di anomalie in gameplay.

---

## Architettura generale

Il flusso del repository è organizzato per fasi:

1. Fase 1: ricerca e smistamento dei video
2. Fase 2: download e clipping dei video in base al tipo
3. Fase 3: rilevamento di freeze/softlock e validazione visiva
4. Fase 4: analisi semantica e classificazione contestuale di qualsiasi anomalia generale rilevata nelle clip sospette

---

## Struttura delle cartelle principali

- `phase1_dispatcher.py`  
  Inizializza la ricerca di video e li classifica in path A/B/C:
  - gameplay da ritagliare;
  - compilations da analizzare visivamente;
  - showcase da scaricare interi.

- `phase2_clipper_gameplays.py`  
  Scarica segmenti di gameplay da video di tipo gameplay e genera JSON con metadata iniziali.

- `phase2_clipping_compilation.py`  
  Scarica compilation, rileva scene con AdaptiveDetector e produce clip separate associate a metadata.

- `phase2_clipping_showcase.py`  
  Scarica showcase completi e li prepara per la successiva analisi semantica.

- `phase3_fast_freeze_detector.py`  
  Rileva freeze tramite differenza di movimento pixel-wise; genera report visivi in modo semplice e rapido.

- `phase3_smart_vision_ocr.py`  
  Versione avanzata del detector con OCR, filtri per menu/UI e produzione di clip anomale. Attualmente il modulo legge il dataset di input da `benchmark_phase3`; se si vuole far prendere in input dallo `smart_vision_ocr` l'output delle Fasi 2, bisogna cambiare la cartella input in `clip_da_analizzare`.

- `phase4_semantic_lmm.py`  
  Analizza le clip con Google Gemini per classificare l'evento come performance, physics, logic o false_positive. Attualmente il suo input predefinito è `clip_da_analizzare`; se si vuole far prendere in input dal `phase4_semantic_lmm.py` l'output di `phase3_smart_vision_ocr.py`, bisogna cambiare l'input dell'LMM in `anomalie_rilevate`.

- `diagramma/`
  Contiene la documentazione grafica dell'architettura del sistema:
  - `architettura_avateg.tex` — sorgente LaTeX del diagramma della pipeline AVATEG.

- `approcci_scartati/`
  Contiene gli approcci ML messi da parte rispetto alla pipeline principale, mantenuti esclusivamente come materiale storico e sperimentale:
  - `phase4_ml_feature_extractor.py`;
  - `phase4_ml_classifier.py`.

---

## Pipeline dettagliata

### 1) Fase 1 - Ricerca e smistamento

`phase1_dispatcher.py` usa `yt_dlp` per cercare video YouTube con query specifica. Per ogni risultato:

- filtra contenuti +18 o age-restricted;
- scarta fail/umoristici, mod esterni e patch non vanilla;
- individua compilation/listicle;
- riconosce showcase dedicati a bug;
- per gameplay standard cerca timestamp in commenti contenenti parole chiave come "bug", "glitch", "stuck", "softlock".

I risultati vengono salvati in `risultati_fase1.json` con tre sezioni:

- `gameplays`
- `compilations`
- `showcases`

---

### 2) Fase 2 - Clipping

#### Gameplay
`phase2_clipper_gameplays.py`

- legge `risultati_fase1.json`;
- raggruppa timestamp trovati in commenti;
- crea clip di 30 secondi intorno al momento sospetto;
- salva `.mp4` in `clip_da_analizzare/gameplays` e JSON con metadata iniziali.

#### Compilation
`phase2_clipping_compilation.py`

- scarica il video completo di una compilation;
- usa `scenedetect` con `AdaptiveDetector`;
- rimuove scene duplicate e troppo brevi/lunghe;
- esporta clip di scena in `clip_da_analizzare/compilations`.

#### Showcase
`phase2_clipping_showcase.py`

- scarica il video intero del showcase;
- salva il file e il JSON di metadata; 
- prepara il contenuto per successiva analisi semantica.

---

### 3) Fase 3 - Rilevamento freeze

#### Rilevatore rapido
`phase3_fast_freeze_detector.py`

- analizza pixel frame-by-frame con differenza assoluta tra frame consecutivi;
- rileva periodi di scarsa variazione;
- salva un report in `reports_vision`.

#### Rilevatore smart con OCR
`phase3_smart_vision_ocr.py`

- usa OpenCV + OCR (Tesseract);
- rileva micro-freeze e softlock;
- scarta falsi positivi dovuti a menu, caricamenti, HUD o transizioni;
- esporta clip critiche nella cartella `anomalie_rilevate` con JSON di analisi.

Configurazione attuale: il modulo è impostato per leggere il dataset di input da `benchmark_phase3`. Se si vuole far prendere in input dallo `smart_vision_ocr` l'output delle Fasi 2, bisogna cambiare la cartella input in `clip_da_analizzare`.

Configurazione attuale: `phase3_smart_vision_ocr.py` usa `benchmark_phase3` come input predefinito; per farlo lavorare con l'output delle Fasi 2, bisogna modificare il percorso di input in `clip_da_analizzare`.

L'output principale è `anomalie_rilevate/`.

---

### 4) Fase 4 - Analisi semantica delle clip

`phase4_semantic_lmm.py`

- legge tutte le JSON di clip in `clip_da_analizzare` in modo ricorsivo;
- per ogni clip:
  - carica il video;
  - invia il video e un prompt contestuale a Gemini;
  - ottiene un JSON con diagnosi semantica;
- salva il risultato in `report_semantici_generali`.

Questa fase non si limita a freeze o softlock: gestisce qualsiasi tipo di anomalia generale visibile nel gameplay, inclusi problemi di performance, fisica, logica, menu/UI e falsi positivi.

Configurazione attuale: il percorso di input predefinito è `clip_da_analizzare`. Se invece si vuole far prendere in input dal `phase4_semantic_lmm.py` l'output di `phase3_smart_vision_ocr.py`, bisogna cambiare l'input dell'LMM in `anomalie_rilevate`.

Il report include:

- `dati_euristici_cpu`
- `diagnosi_semantica_ia`

Gli script ML presenti in `approcci_scartati` non fanno parte della fase 4 operativa descritta qui e non sono necessari per eseguire la pipeline principale.

---

## Requisiti e dipendenze

Il progetto richiede Python 3.10+ e le seguenti librerie principali:

- `yt_dlp`
- `opencv-python`
- `numpy`
- `pandas`
- `scikit-learn`
- `scenedetect`
- `pytesseract`
- `python-dotenv`
- `google-genai`
- `thefuzz`

Per il riconoscimento OCR è necessario installare Tesseract OCR sul sistema e configurare il path in:

- `phase3_smart_vision_ocr.py`

---

## Configurazione iniziale

1. Crea un ambiente virtuale Python.
2. Installa le dipendenze.
3. Verifica che esista il file `cookies.txt` per le richieste YouTube se necessario.
4. Crea un file `.env` o `file.env` con le variabili richieste dal client Gemini.
5. Assicurati che `Tesseract` sia installato e accessibile.

Esempio di file ambientale:

```env
GOOGLE_API_KEY=your_api_key_here
```

---

## Ordine di esecuzione consigliato

1. `phase1_dispatcher.py`  
   Ricerca video e genera `risultati_fase1.json`

2. `phase2_clipper_gameplays.py`  
   `phase2_clipping_compilation.py`  
   `phase2_clipping_showcase.py`  
   Genera clip da analizzare

3. `phase3_fast_freeze_detector.py`  
   oppure `phase3_smart_vision_ocr.py`  
   Rileva freeze e produce report visivi

4. `phase4_semantic_lmm.py`  
   Revisione semantica delle clip con Gemini per classificare qualsiasi anomalia generale

---

## Output generati

Il repository produce diversi tipi di artefatti:

- `risultati_fase1.json`: routing dei video
- `clip_da_analizzare/...`: clip generate per gameplay, compilation e showcase
- `reports_vision/...`: report visivi di freeze
- `anomalie_rilevate/...`: clip anomale tagliate e validate; sono da considerare output alternativo, non il percorso di input corrente del phase4
- `report_semantici_benchmark/...`: risultati prodotti dal modulo LMM per i video presenti nel dataset benchmark
- `report_semantici_generali/...`: report finali unificati

La cartella `approcci_scartati` contiene codice ML sperimentale separato dalla pipeline principale e non rappresenta un passaggio obbligatorio del flusso operativo.

---

## Note importanti

- Questa repository è pensata per workflow di analisi e ricerca video, non per un'applicazione web o un modulo esportabile come libreria.
- Sono presenti script di benchmark e validazione scientifica, ma il cuore del progetto è la pipeline end-to-end di rilevazione anomalia.
- I file generati `.json` e `.mp4` sono artefatti di output e non rappresentano il codice applicativo del sistema.
- L'analisi LMM richiede accesso a API esterne e dipende da quota, disponibilità del servizio e corretto setup dell'ambiente.

---

## Riassunto

AVATEG combina approcci differenti per rendere automatica la scoperta di bug in gameplay video:

- ricerca intelligente di contenuti su YouTube;
- clustering temporale di segnali sospetti;
- rilevamento visivo di freeze tramite computer vision;
- validazione semantica delle clip sospette tramite analisi contestuale per qualsiasi tipo di anomalia generale.

Questo rende il framework utile come pipeline di QA automatizzata per videogiochi, soprattutto per riconoscere softlock, micro-stutter, problemi di fisica, logica, menu/UI e falsi positivi in materiale video di gameplay.

---

## Precisazione

Questo progetto è stato sviluppato nell’ambito del tirocinio e della tesi del corso di Fondamenti di Intelligenza Artificiale dell’Università degli Studi di Salerno.
