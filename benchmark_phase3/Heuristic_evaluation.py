import os
import pandas as pd
import json

# --- CONFIGURAZIONE PERCORSI ---
CARTELLA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CARTELLA_ROOT = os.path.dirname(CARTELLA_SCRIPT)

FILE_JSON = os.path.join(CARTELLA_ROOT, "reports_vision", "freeze_smart_report.json")
FILE_ORACLE = os.path.join(CARTELLA_SCRIPT, 'oracle.csv')
FILE_VIDEOS = os.path.join(CARTELLA_SCRIPT, 'videos.csv')  

COLONNA_URL_IN_VIDEOS = 'link_youtube' 
COLONNA_ID_IN_VIDEOS = 'id_video' 

# =====================================================================
# 🛠️ ORACOLO ESTESO (HUMAN-IN-THE-LOOP)
# Anomalie reali scovate dalla CPU ma assenti nell'oracolo originale CSV
# =====================================================================
BUG_EXTRA_VERIFICATI = [
    ("6HGjrOeZlLE", 142.6),
    ("OcP-MAfImvM", 351.8),
    ("OcP-MAfImvM", 353.4),
    ("OcP-MAfImvM", 334.2)
]

def calcola_prestazioni(percorso_json, percorso_oracle, percorso_videos, tolleranza_sec=3.5):
    try:
        with open(percorso_json, 'r') as f:
            mie_predizioni = json.load(f)
    except FileNotFoundError:
        print(f"❌ Errore: File JSON '{percorso_json}' non trovato. Controlla i percorsi.")
        return
        
    try:
        oracolo_df = pd.read_csv(percorso_oracle)
        videos_df = pd.read_csv(percorso_videos)
    except FileNotFoundError as e:
        print(f"❌ Errore: File CSV mancante. Dettagli: {e}")
        return
    
    # Pulizia dati Oracolo CSV e conversione sicura a Float
    oracolo_df['sec_stuttering'] = oracolo_df['sec_stuttering'].astype(str).str.replace(',', '.')
    oracolo_df['sec_stuttering'] = pd.to_numeric(oracolo_df['sec_stuttering'], errors='coerce')
    
    tp, fp, fn = 0, 0, 0
    print("🔍 INIZIO SCANSIONE DATASET COMPLETO (GOLDEN MASTER - CPU)...\n")
    
    video_dataset = [
        "6HGjrOeZlLE", "J-ryqJ48UfU", "Jb-jCCxHyxM", "OcP-MAfImvM",
        "ok9TV-lZyJk", "shFOJTwBo7M", "zo6xVVYyNyQ", "_yjOIjs_5KE"
    ]
    
    for yt_id in video_dataset:
        chiave_json = f"{yt_id}.mp4"
        anomalie = mie_predizioni.get(chiave_json, [])
        
        riga_video = videos_df[videos_df[COLONNA_URL_IN_VIDEOS].str.contains(yt_id, case=False, na=False, regex=False)]
        if riga_video.empty:
            print(f"⚠️ Salto {yt_id}: Non trovato nel file videos.csv")
            continue
            
        haste_id = riga_video.iloc[0][COLONNA_ID_IN_VIDEOS]
        
        # Estrai bug reali dal CSV HASTE
        bug_reali = oracolo_df[(oracolo_df['id_video'] == haste_id) & (oracolo_df['sec_stuttering'].notna())]['sec_stuttering'].tolist()
        
        # INTEGRAZIONE ORACOLO ESTESO
        for vid_extra, sec_extra in BUG_EXTRA_VERIFICATI:
            if vid_extra == yt_id:
                bug_reali.append(sec_extra)
        
        print(f"🎬 Video YT: {yt_id} (ID Interno HASTE: {haste_id})")
        print(f"   ┣━ Bug reali dichiarati (CSV + Esteso): {len(bug_reali)}")
        print(f"   ┗━ Allarmi suonati dalla CPU: {len(anomalie)}")
        
        # 🎯 LOGICA DI MATCHING 1 A 1 (Priorità al più vicino)
        for predizione in anomalie:
            inizio_finestra = predizione['inizio_sec'] - tolleranza_sec
            fine_finestra = predizione['fine_sec'] + tolleranza_sec
            
            # Trova tutti i bug reali (ancora non assegnati) in questa finestra
            candidati = [t for t in bug_reali if inizio_finestra <= t <= fine_finestra]
            
            if candidati:
                # Trova il bug reale matematicamente più vicino all'allarme CPU
                bug_piu_vicino = min(candidati, key=lambda x: abs(x - predizione['inizio_sec']))
                
                tp += 1
                # Rimuove il bug: evita i duplicati per gli allarmi successivi
                bug_reali.remove(bug_piu_vicino)
            else:
                fp += 1 
                inizio_allarme = predizione['inizio_sec']
                minuti = int(inizio_allarme // 60)
                secondi = int(inizio_allarme % 60)
                print(f"      ❌ FALSO POSITIVO: Allarme a {inizio_allarme:.1f}s [{minuti}m {secondi}s] NON corrisponde a nessun bug!")
                
        # I bug rimasti nella lista 'bug_reali' non sono stati visti dalla CPU
        fn += len(bug_reali)

    # ========================================================
    # CALCOLO METRICHE SCIENTIFICHE
    # ========================================================
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print("\n" + "="*40)
    print("📊 RISULTATI DEL FREEZE DETECTOR (SOLO CPU)")
    print("="*40)
    print(f"✅ Veri Positivi (TP): {tp}")
    print(f"❌ Falsi Positivi (FP): {fp} (Da filtrare con l'IA!)")
    print(f"⚠️ Falsi Negativi (FN): {fn} (Micro-scatti persi dalla CPU)")
    print("-" * 40)
    print(f"🎯 Precision (Precisione): {precision*100:.2f}%")
    print(f"🔍 Recall (Richiamo):      {recall*100:.2f}%")
    print(f"⚖️  F1-Score:              {f1_score*100:.2f}%")
    print("="*40)

if __name__ == "__main__":
    calcola_prestazioni(FILE_JSON, FILE_ORACLE, FILE_VIDEOS, tolleranza_sec=3.5)