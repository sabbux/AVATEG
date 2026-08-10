import yt_dlp
import json
import os
import re
import glob
from datetime import datetime

CARTELLA_OUTPUT = "clip_da_analizzare/gameplays"

# Per prevenire problemi di filesystem con caratteri speciali, puliamo i titoli rimuovendo caratteri speciali e limitando la lunghezza
def pulisci_nome(s):
    return re.sub(r'[\\/*?:"<>|]', "", s).replace(" ", "_")[:50]

def timestamp_a_secondi(ts_string):
    parti = ts_string.split(':')
    try:
        if len(parti) == 2: return int(parti[0]) * 60 + int(parti[1])
        elif len(parti) == 3: return int(parti[0]) * 3600 + int(parti[1]) * 60 + int(parti[2])
    except: return 0
    return 0

def clusterizza_timestamp(timestamps_list, soglia=20):
    if not timestamps_list: return []
    sec_ordinati = sorted([timestamp_a_secondi(ts) for ts in timestamps_list])
    cluster, gruppo = [], [sec_ordinati[0]]
    for s in sec_ordinati[1:]:
        if s - gruppo[-1] <= soglia: gruppo.append(s)
        else:
            cluster.append(sum(gruppo) // len(gruppo))
            gruppo = [s]
    if gruppo: cluster.append(sum(gruppo) // len(gruppo))
    return cluster

def svuota_cartella(cartella):
    """Svuota la cartella da file vecchi (.mp4 e .json) per risparmiare token."""
    if not os.path.exists(cartella): return
    files = glob.glob(os.path.join(cartella, "*"))
    for f in files:
        try:
            os.remove(f)
        except Exception as e:
            print(f"   [Avviso] Impossibile eliminare {f}: {e}")

def esegui_clipping_gameplay(file_json="risultati_fase1.json"):
    print("🎬 FASE 2: Clipping NLP per Gameplay e Generazione JSON")
    
    if not os.path.exists(file_json): 
        print("❌ File risultati_fase1.json non trovato.")
        return
        
    with open(file_json, 'r', encoding='utf-8') as f:
        dati = json.load(f)
        
    os.makedirs(CARTELLA_OUTPUT, exist_ok=True)
    
    # 🧹 PULIZIA INIZIALE
    print(f"🧹 Pulizia della cartella {CARTELLA_OUTPUT} in corso...")
    svuota_cartella(CARTELLA_OUTPUT)
    
    for video in dati.get("gameplays", []):
        titolo_legge = pulisci_nome(video['titolo'])
        url_video = video['url']
        momenti = clusterizza_timestamp(video['timestamps_grezzi'])
        
        for sec in momenti:
            start, end = max(0, sec - 15), sec + 15
            nome_base = f"{titolo_legge}_{start}s"
            percorso_clip = os.path.join(CARTELLA_OUTPUT, f"{nome_base}.mp4")
            percorso_json = os.path.join(CARTELLA_OUTPUT, f"{nome_base}.json")
            
            print(f"   [+] Scarico Clip e preparo JSON: {video['titolo']} ({start}s-{end}s)")
            
            ydl_opts = {
                'format': '18/worst',
                'outtmpl': percorso_clip,
                'download_ranges': yt_dlp.utils.download_range_func(None, [(start, end)]),
                'force_keyframes_at_cuts': True,
                'quiet': True,
                'no_warnings': True
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: 
                    ydl.download([url_video])
                    
                dati_metadati = {
                    "dati_euristici_cpu": {
                        "video_originale": url_video,
                        "titolo_youtube": video['titolo'],
                        "inizio_sec": start,
                        "finestra_temporale": {
                            "start": start,
                            "end": end
                        },
                        "tipo_anomalia_sospetta": "segnalazione_community_nlp",
                        "fonte": "YouTube NLP Engine",
                        "data_generazione": datetime.now().isoformat()
                    },
                    "diagnosi_semantica_ia": {} 
                }
                
                with open(percorso_json, 'w', encoding='utf-8') as f:
                    json.dump(dati_metadati, f, indent=4)
                    
                print(f"   ✅ JSON salvato per LMM.")
                    
            except Exception as e: 
                print(f"   ❌ Errore durante l'elaborazione: {e}")
                if os.path.exists(percorso_clip): os.remove(percorso_clip)

if __name__ == "__main__":
    esegui_clipping_gameplay()