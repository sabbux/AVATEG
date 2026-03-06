import yt_dlp
import json
import os

CARTELLA_OUTPUT = "clip_generate/gameplay"

def timestamp_a_secondi(ts_string):
    parti = ts_string.split(':')
    try:
        if len(parti) == 2: return int(parti[0]) * 60 + int(parti[1])
        elif len(parti) == 3: return int(parti[0]) * 3600 + int(parti[1]) * 60 + int(parti[2])
    except ValueError: return 0
    return 0

def clusterizza_timestamp(timestamps_list, soglia=20):
    if not timestamps_list: return []
    sec_ordinati = sorted([timestamp_a_secondi(ts) for ts in timestamps_list])
    cluster = []
    gruppo = [sec_ordinati[0]]

    for s in sec_ordinati[1:]:
        if s - gruppo[-1] <= soglia: gruppo.append(s)
        else:
            cluster.append(sum(gruppo) // len(gruppo))
            gruppo = [s]
    if gruppo: cluster.append(sum(gruppo) // len(gruppo))
    return cluster

def esegui_clipping_gameplay(file_json="risultati_fase1.json"):
    print("🎬 FASE 2: Clipping NLP per Gameplay")
    if not os.path.exists(file_json): return print("File JSON mancante!")
    
    with open(file_json, 'r', encoding='utf-8') as f:
        dati = json.load(f)
        
    gameplays = dati.get("gameplays", [])
    if not gameplays: return print("Nessun gameplay da processare nel JSON.")

    os.makedirs(CARTELLA_OUTPUT, exist_ok=True)

    for video in gameplays:
        print(f"\n► Elaboro: {video['titolo']}")
        momenti_unici = clusterizza_timestamp(video['timestamps_grezzi'])
        
        for sec_centrali in momenti_unici:
            start, end = max(0, sec_centrali - 15), sec_centrali + 15
            nome_file = f"{CARTELLA_OUTPUT}/gameplay_{video['video_id']}_{start}s_{end}s.mp4"
            
            if os.path.exists(nome_file): continue
            
            print(f"   [+] Scarico clip da {start}s a {end}s...")
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': nome_file, 'quiet': True, 'no_warnings': True,
                'download_ranges': yt_dlp.utils.download_range_func(None, [(start, end)]),
                'force_keyframes_at_cuts': True 
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([video['url']])
            except Exception as e: print(f"   ❌ Errore: {e}")

if __name__ == "__main__":
    esegui_clipping_gameplay()