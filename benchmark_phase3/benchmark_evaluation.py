import os
import pandas as pd
import json

# --- CONFIGURAZIONE ASSOLUTA ---
CARTELLA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
FILE_JSON = r"C:\Users\checc\AVATEG\AVATEG\reports_vision\freeze_smart_report.json"
FILE_ORACLE = os.path.join(CARTELLA_SCRIPT, 'oracle.csv')
FILE_VIDEOS = os.path.join(CARTELLA_SCRIPT, 'videos.csv')  

# ⚠️ NOMI DELLE COLONNE ESATTI COME NEL TUO CSV
COLONNA_URL_IN_VIDEOS = 'link_youtube' 
COLONNA_ID_IN_VIDEOS = 'id_video' 

def calcola_prestazioni(percorso_json, percorso_oracle, percorso_videos, tolleranza_sec=3):
    with open(percorso_json, 'r') as f:
        mie_predizioni = json.load(f)
        
    try:
        oracolo_df = pd.read_csv(percorso_oracle)
        videos_df = pd.read_csv(percorso_videos)
    except FileNotFoundError as e:
        print(f"❌ Errore: File CSV mancante. Dettagli: {e}")
        return
    
    # 🛡️ PULIZIA DATI
    oracolo_df['sec_stuttering'] = pd.to_numeric(oracolo_df['sec_stuttering'], errors='coerce')
    
    tp, fp, fn = 0, 0, 0
    print("🔍 INIZIO SCANSIONE SUL DATASET COMPLETO...\n")
    
    # 🟢 LISTA MASTER: I video che compongono il tuo dataset di test.
    # Questo garantisce che NESSUN video venga saltato, anche se non ha allarmi nel JSON.
    video_dataset = [
        "6HGjrOeZlLE", "J-ryqJ48UfU", "Jb-jCCxHyxM", "OcP-MAfImvM",
        "ok9TV-lZyJk", "shFOJTwBo7M", "zo6xVVYyNyQ", "_yjOIjs_5KE"
    ]
    
    for yt_id in video_dataset:
        
        # 1. Recupera le anomalie. Se il video non c'è nel JSON (0 allarmi), restituisce []
        chiave_json = f"{yt_id}.mp4"
        anomalie = mie_predizioni.get(chiave_json, []) # <-- IL TRUCCO È QUI
        
        # 2. Trova il video nel CSV
        riga_video = videos_df[videos_df[COLONNA_URL_IN_VIDEOS].str.contains(yt_id, case=False, na=False, regex=False)]
        
        if riga_video.empty:
            print(f"⚠️ Salto {yt_id}: Non trovato nel file videos.csv")
            continue
            
        haste_id = riga_video.iloc[0][COLONNA_ID_IN_VIDEOS]
        
        # 3. Estrai i bug reali
        bug_reali = oracolo_df[(oracolo_df['id_video'] == haste_id) & (oracolo_df['sec_stuttering'].notna())]['sec_stuttering'].tolist()
        
        print(f"🎬 Video YT: {yt_id} (ID Interno HASTE: {haste_id})")
        print(f"   ┣━ Bug reali dichiarati: {len(bug_reali)}")
        print(f"   ┗━ Allarmi suonati: {len(anomalie)}")
        
        # --- LOGICA DI MATCHING CON TOLLERANZA ---
        for predizione in anomalie:
            inizio_finestra = predizione['inizio_sec'] - tolleranza_sec
            fine_finestra = predizione['fine_sec'] + tolleranza_sec
            
            match_trovato = False
            oracoli_assorbiti = []
            
            for tempo_reale in bug_reali:
                if inizio_finestra <= tempo_reale <= fine_finestra:
                    match_trovato = True
                    oracoli_assorbiti.append(tempo_reale)
            
            if match_trovato:
                tp += 1
                for oracolo in oracoli_assorbiti:
                    bug_reali.remove(oracolo)
            else:
                fp += 1 
                inizio_allarme = predizione['inizio_sec']
                minuti = int(inizio_allarme // 60)
                secondi = int(inizio_allarme % 60)
                
                print(f"      ❌ FALSO POSITIVO: Allarme a {inizio_allarme:.1f}s [{minuti}m {secondi}s] NON corrisponde a nessun bug!")
                
        # Tutti i bug che non sono stati "catturati" rimangono nella lista e diventano FN
        fn += len(bug_reali)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    print("\n" + "="*40)
    print(f"📊 RISULTATI DEL TUO FREEZE DETECTOR")
    print("="*40)
    print(f"✅ Veri Positivi (TP): {tp}")
    print(f"❌ Falsi Positivi (FP): {fp}")
    print(f"⚠️ Falsi Negativi (FN): {fn}")
    print("-"*40)
    print(f"🎯 Precision: {precision*100:.2f}%")
    print(f"🔍 Recall:    {recall*100:.2f}%")
    print("="*40)

calcola_prestazioni(FILE_JSON, FILE_ORACLE, FILE_VIDEOS, tolleranza_sec=3)