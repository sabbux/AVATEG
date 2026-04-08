import yt_dlp
import json
import os
import re

CARTELLA_OUTPUT = "clip_generate/showcase"

def pulisci_nome_file(stringa):
    # Rimuove caratteri non consentiti nei nomi file (Windows/Linux/Mac)
    return re.sub(r'[\\/*?:"<>|]', "", stringa).replace(" ", "_")

def esegui_download_showcase(file_json="risultati_fase1.json"):
    print("\n🔍 FASE 2: Download Showcase (Nomi file leggibili)")
    if not os.path.exists(file_json): 
        return print("File JSON mancante!")

    with open(file_json, 'r', encoding='utf-8') as f:
        dati = json.load(f)

    showcases = dati.get("showcases", [])
    if not showcases: 
        return print("Nessun showcase da processare.")

    os.makedirs(CARTELLA_OUTPUT, exist_ok=True)

    for video in showcases:
        titolo_pulito = pulisci_nome_file(video['titolo'])
        video_url = video['url']
        
        # Costruiamo il nome file usando il titolo leggibile
        nome_file = f"{CARTELLA_OUTPUT}/{titolo_pulito}.mp4"

        print(f"\n► Download: {video['titolo']}")

        if os.path.exists(nome_file):
            print("   [-] Già presente, salto.")
            continue
            
        ydl_opts = {
            'format': '18/worst', 
            'outtmpl': nome_file, # Usa il titolo pulito qui
            'quiet': False, 
            'no_warnings': False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_dl:
                ydl_dl.download([video_url])
            print(f"   ✅ Salvato come: {titolo_pulito}.mp4")
        except Exception as e:
            print(f"   ❌ Errore: {e}")

if __name__ == "__main__":
    esegui_download_showcase()