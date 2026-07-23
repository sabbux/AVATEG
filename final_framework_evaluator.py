import os
import json
import glob
import pandas as pd

# --- CONFIGURAZIONE PERCORSI (DALLA ROOT) ---
# La cartella root è quella dove si trova questo script
CARTELLA_ROOT = os.path.dirname(os.path.abspath(__file__))

# Puntiamo alle sottocartelle corrette
FILE_ORACLE = os.path.join(CARTELLA_ROOT, 'benchmark_phase3', 'oracle.csv')
FILE_VIDEOS = os.path.join(CARTELLA_ROOT, 'benchmark_phase3', 'videos.csv')  
CARTELLA_REPORT_LMM = os.path.join(CARTELLA_ROOT, 'report_semantici')

COLONNA_URL_IN_VIDEOS = 'link_youtube' 
COLONNA_ID_IN_VIDEOS = 'id_video' 

# =====================================================================
# 🛠️ ORACOLO ESTESO (HUMAN-IN-THE-LOOP)
# Anomalie reali che OpenCV ha scovato oltre l'annotazione umana
# =====================================================================
BUG_EXTRA_VERIFICATI = [
    ("6HGjrOeZlLE", 142.6),
    ("OcP-MAfImvM", 351.8),
    ("OcP-MAfImvM", 353.4),
    ("OcP-MAfImvM", 334.2)  # Bug con 1 sec di fluidità confermato da QA
]

def valuta_framework_ibrido(tolleranza_sec=3.5):
    print("⚖️ VALUTAZIONE FRAMEWORK AVATEG (OpenCV + LMM) - MAPPING 1:1")
    print("================================================================\n")
        
    try:
        oracolo_df = pd.read_csv(FILE_ORACLE)
        videos_df = pd.read_csv(FILE_VIDEOS)
    except FileNotFoundError as e:
        print(f"❌ Errore: File CSV mancante. Assicurati che 'benchmark_phase3' esista. Dettagli: {e}")
        return
    
    # 1. Caricamento Predizioni IA (LMM)
    lmm_predictions = {}
    file_reports = glob.glob(os.path.join(CARTELLA_REPORT_LMM, "*.json"))
    
    if not file_reports:
        print(f"❌ Errore: Nessun file JSON trovato in {CARTELLA_REPORT_LMM}")
        return

    for file_path in file_reports:
        with open(file_path, "r", encoding="utf-8") as f:
            dati = json.load(f)
            
        video_orig = os.path.basename(dati.get("dati_euristici_cpu", {}).get("video_originale", ""))
        video_name = video_orig.replace(".mp4", "")
        sec_inizio = dati.get("dati_euristici_cpu", {}).get("inizio_sec", 0.0)

        fault_type = dati.get("diagnosi_semantica_ia", {}).get("evento_fault", {}).get("fault_type", "sconosciuto").lower()
        ia_dice_bug = "stutter" in fault_type or "freeze" in fault_type

        if video_name not in lmm_predictions:
            lmm_predictions[video_name] = []

        lmm_predictions[video_name].append({
            'inizio_sec': sec_inizio,
            'ia_dice_bug': ia_dice_bug,
            'motivo': fault_type
        })
        
    oracolo_df['sec_stuttering'] = oracolo_df['sec_stuttering'].astype(str).str.replace(',', '.')
    oracolo_df['sec_stuttering'] = pd.to_numeric(oracolo_df['sec_stuttering'], errors='coerce')
    
    tp, fp, fn, tn = 0, 0, 0, 0
    lista_tp, lista_fp, lista_tn, lista_fn_ia = [], [], [], []
    
    video_dataset = [
        "6HGjrOeZlLE", "J-ryqJ48UfU", "Jb-jCCxHyxM", "OcP-MAfImvM",
        "ok9TV-lZyJk", "shFOJTwBo7M", "zo6xVVYyNyQ", "_yjOIjs_5KE"
    ]
    
    for yt_id in video_dataset:
        riga_video = videos_df[videos_df[COLONNA_URL_IN_VIDEOS].str.contains(yt_id, case=False, na=False, regex=False)]
        if riga_video.empty: continue
            
        haste_id = riga_video.iloc[0][COLONNA_ID_IN_VIDEOS]
        bug_reali = oracolo_df[(oracolo_df['id_video'] == haste_id) & (oracolo_df['sec_stuttering'].notna())]['sec_stuttering'].tolist()
        
        for vid_extra, sec_extra in BUG_EXTRA_VERIFICATI:
            if vid_extra == yt_id: bug_reali.append(sec_extra)
        
        # Ordiniamo gli allarmi in ordine cronologico per il Greedy Matching
        allarmi_lmm = sorted(lmm_predictions.get(yt_id, []), key=lambda x: x['inizio_sec'])
        
        for predizione in allarmi_lmm:
            inizio_finestra = predizione['inizio_sec'] - tolleranza_sec
            fine_finestra = predizione['inizio_sec'] + tolleranza_sec
            
            candidati = [t for t in bug_reali if inizio_finestra <= t <= fine_finestra]
            etichetta = f"{yt_id} @ {predizione['inizio_sec']:.1f}s"
            
            if candidati:
                bug_piu_vicino = min(candidati, key=lambda x: abs(x - predizione['inizio_sec']))
                bug_reali.remove(bug_piu_vicino)
                
                if predizione['ia_dice_bug']:
                    tp += 1
                    lista_tp.append(etichetta)
                else:
                    fn += 1
                    lista_fn_ia.append(f"{etichetta} (IA l'ha scartato come {predizione['motivo']})")
            else:
                # La CPU ha lanciato un allarme ma NON ci sono bug reali (Falso Allarme CPU)
                if predizione['ia_dice_bug']:
                    fp += 1 # L'IA è caduta in trappola
                    lista_fp.append(etichetta)
                else:
                    tn += 1 # IL SUCCESSO! L'IA ha disinnescato il falso allarme
                    lista_tn.append(etichetta)
                    
        # I bug rimasti nella lista non sono MAI stati visti dalla CPU
        fn += len(bug_reali)

    print(f"✅ TRUE POSITIVES (Bug confermati da IA): {len(lista_tp)}")
    print(f"🛡️  TRUE NEGATIVES (Falsi allarmi CPU disinnescati da IA): {len(lista_tn)}")
    for x in lista_tn: print(f"    - {x} 🎯 Salvato!")
    print(f"❌ FALSE POSITIVES (Falsi allarmi CPU confermati da IA): {len(lista_fp)}")
    print(f"⚠️ FALSE NEGATIVES TOTALI: {fn}")
    print(f"    Di cui scartati per errore dall'IA: {len(lista_fn_ia)}")
    for x in lista_fn_ia: print(f"    - {x}")

    # CALCOLO METRICHE
    totale_casi = tp + fp + fn + tn
    accuracy = (tp + tn) / totale_casi if totale_casi > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print("\n" + "="*50)
    print("📊 METRICHE SCIENTIFICHE: AVATEG (OpenCV + LMM)")
    print("="*50)
    print(f"🎯 Precision (Precisione) : {precision*100:.2f}%")
    print(f"🔍 Recall (Richiamo)      : {recall*100:.2f}%")
    print(f"⚖️  F1-Score               : {f1_score*100:.2f}%")
    print("==================================================")

if __name__ == "__main__":
    valuta_framework_ibrido()