import yt_dlp
import json
import os
import re

CARTELLA_OUTPUT = "clip_generate/gameplay"

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

def esegui_clipping_gameplay(file_json="risultati_fase1.json"):
    print("🎬 FASE 2: Clipping NLP per Gameplay")
    if not os.path.exists(file_json): return
    with open(file_json, 'r', encoding='utf-8') as f:
        dati = json.load(f)
        
    os.makedirs(CARTELLA_OUTPUT, exist_ok=True)
    for video in dati.get("gameplays", []):
        titolo_legge = pulisci_nome(video['titolo'])
        momenti = clusterizza_timestamp(video['timestamps_grezzi'])
        
        for sec in momenti:
            start, end = max(0, sec - 15), sec + 15
            nome_file = f"{CARTELLA_OUTPUT}/{titolo_legge}_{start}s.mp4"
            
            if os.path.exists(nome_file): continue
            
            print(f"   [+] Clip da {video['titolo']} ({start}s-{end}s)")
            ydl_opts = {
                'format': '18/worst', # SICUREZZA ANTI-BLOCCO
                'outtmpl': nome_file,
                'download_ranges': yt_dlp.utils.download_range_func(None, [(start, end)]),
                'force_keyframes_at_cuts': True,
                'quiet': True
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([video['url']])
            except Exception as e: print(f"   ❌ Errore: {e}")

if __name__ == "__main__":
    esegui_clipping_gameplay()