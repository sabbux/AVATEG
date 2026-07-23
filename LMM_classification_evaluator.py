import os
import json
import glob
import pandas as pd

# =====================================================================
# 🛠️ ORACOLO ESTESO (HUMAN-IN-THE-LOOP)
# Le anomalie reali scovate dalla CPU ma assenti nell'oracolo originale
# =====================================================================
BUG_EXTRA_VERIFICATI = [
    ("6HGjrOeZlLE", 142.6), # Vero bug scovato, l'LMM lo aveva confermato
    ("OcP-MAfImvM", 351.8), # Vero bug scovato, l'LMM lo aveva scartato erroneamente
    ("OcP-MAfImvM", 353.4), # Vero bug scovato, l'LMM lo aveva scartato erroneamente
    ("OcP-MAfImvM", 334.2)
]

def calcola_matrice_confusione():
    print("⚖️ INCROCIO DATI: REPORT LMM vs ORACLE HASTE (CON ORACOLO ESTESO)")
    print("========================================================\n")

    # 1. Carica l'Oracolo puntando alla cartella benchmark_phase3
    percorso_oracolo = os.path.join("benchmark_phase3", "oracle.csv")
    try:
        df_oracle = pd.read_csv(percorso_oracolo)
    except FileNotFoundError:
        print(f"❌ ERRORE: File '{percorso_oracolo}' non trovato!")
        return

    # Mappatura ID -> Nome Video
    video_mapping = {
        1: 'zo6xVVYyNyQ', 2: '6HGjrOeZlLE', 4: 'ok9TV-lZyJk', 5: 'shFOJTwBo7M',
        7: 'OcP-MAfImvM', 8: 'Jb-jCCxHyxM', 9: '_yjOIjs_5KE', 10: 'J-ryqJ48UfU'
    }

    # Creiamo un dizionario super-veloce per l'Oracolo { "nome_video": [sec1, sec2, ...] }
    oracolo_dict = {}
    for _, row in df_oracle.iterrows():
        vid_name = video_mapping.get(row['id_video'])
        if vid_name:
            if vid_name not in oracolo_dict:
                oracolo_dict[vid_name] = []
            
            raw_sec = str(row['sec_stuttering']).replace(',', '.').strip()
            try:
                sec_val = float(raw_sec)
                oracolo_dict[vid_name].append(sec_val)
            except ValueError:
                pass

    # 2. Legge i JSON dell'LMM
    file_reports = glob.glob(os.path.join("report_semantici", "*.json"))
    
    tp = [] # Bug Reali confermati
    tn = [] # Falsi allarmi disinnescati 
    fp = [] # Falsi allarmi confermati come bug
    fn = [] # Bug Reali scartati come menù 
    nuove_scoperte = []

    for file_path in file_reports:
        with open(file_path, "r", encoding="utf-8") as f:
            dati = json.load(f)

        video_orig = os.path.basename(dati.get("dati_euristici_cpu", {}).get("video_originale", ""))
        video_name = video_orig.replace(".mp4", "")
        sec_inizio = dati.get("dati_euristici_cpu", {}).get("inizio_sec", 0.0)

        if "diagnosi_semantica_ia" in dati:
            fault_type = dati["diagnosi_semantica_ia"]["evento_fault"]["fault_type"].lower()
        else:
            fault_type = "sconosciuto"

        ia_dice_bug = "stutter" in fault_type or "freeze" in fault_type

        # 1. Controlliamo l'oracolo originale (CSV)
        oracolo_dice_bug = False
        is_extra = False
        
        if video_name in oracolo_dict:
            for real_sec in oracolo_dict[video_name]:
                if abs(real_sec - sec_inizio) <= 3.5:
                    oracolo_dice_bug = True
                    break

        # 2. Controlliamo l'Oracolo Esteso se il CSV non l'aveva
        if not oracolo_dice_bug:
            for extra_vid, extra_sec in BUG_EXTRA_VERIFICATI:
                if extra_vid == video_name and abs(extra_sec - sec_inizio) <= 3.5:
                    oracolo_dice_bug = True
                    is_extra = True
                    break

        # CLASSIFICAZIONE NELLA MATRICE
        etichetta = f"{video_name} @ {sec_inizio:.1f}s"
        
        if oracolo_dice_bug and ia_dice_bug:
            tp.append(etichetta)
            if is_extra: nuove_scoperte.append(etichetta)
        elif not oracolo_dice_bug and not ia_dice_bug:
            tn.append(etichetta)
        elif not oracolo_dice_bug and ia_dice_bug:
            fp.append(etichetta)
        elif oracolo_dice_bug and not ia_dice_bug:
            fn.append((etichetta, fault_type)) 

    # 3. Stampa della Matrice di Confusione
    print(f"✅ TRUE POSITIVES ({len(tp)}): L'IA ha confermato un bug reale")
    for x in tp:
        marker = " (🌟 NUOVA SCOPERTA non in oracolo!)" if x in nuove_scoperte else ""
        print(f"   - {x}{marker}")
        
    print("\n--------------------------------------------------------")
    print(f"🛡️  TRUE NEGATIVES ({len(tn)}): L'IA ha scartato un falso allarme della CPU")
    for x in tn: print(f"   - {x}")
    
    print("\n--------------------------------------------------------")
    print(f"❌ FALSE POSITIVES ({len(fp)}): L'IA si è fatta ingannare confermando un falso allarme")
    if not fp:
        print("   - Nessuno! 🎯")
    else:
        for x in fp: print(f"   - {x}")
    
    print("\n--------------------------------------------------------")
    print(f"☠️  FALSE NEGATIVES ({len(fn)}): L'IA ha derubricato a menù un bug VERO")
    for x, motivo in fn: print(f"   - {x} (Scartato come: {motivo})")
    
    # ========================================================
    # 4. CALCOLO DELLE METRICHE SCIENTIFICHE
    # ========================================================
    num_tp = len(tp)
    num_tn = len(tn)
    num_fp = len(fp)
    num_fn = len(fn)
    totale_casi = num_tp + num_tn + num_fp + num_fn

    # Protezione matematica per evitare la divisione per zero
    accuracy = (num_tp + num_tn) / totale_casi if totale_casi > 0 else 0
    precision = num_tp / (num_tp + num_fp) if (num_tp + num_fp) > 0 else 0
    recall = num_tp / (num_tp + num_fn) if (num_tp + num_fn) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print("\n========================================================")
    print("📊 METRICHE SCIENTIFICHE UFFICIALI (AVATEG Framework)")
    print("========================================================")
    print(f"Campione Totale (N)        : {totale_casi} clip analizzate")
    print(f"✔️  Accuracy  (Accuratezza) : {accuracy * 100:.1f}%")
    print(f"🎯 Precision (Precisione)  : {precision * 100:.1f}%")
    print(f"📈 Recall    (Richiamo)    : {recall * 100:.1f}%")
    print(f"⚖️  F1-Score               : {f1_score * 100:.1f}%")
    print("========================================================")

if __name__ == "__main__":
    calcola_matrice_confusione()