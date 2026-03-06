import yt_dlp
import json
import os

CARTELLA_OUTPUT = "clip_generate/showcase"

def esegui_download_showcase(file_json="risultati_fase1.json"):
    print("🔍 FASE 2: Download Completo per Showcase")
    if not os.path.exists(file_json): 
        return print("File JSON mancante!")

    with open(file_json, 'r', encoding='utf-8') as f:
        dati = json.load(f)

    showcases = dati.get("showcases", [])
    if not showcases: 
        return print("Nessun showcase da processare nel JSON.")

    os.makedirs(CARTELLA_OUTPUT, exist_ok=True)

    for video in showcases:
        print(f"\n► Elaboro Showcase: {video['titolo']}")
        video_url = video['url']
        video_id = video['video_id']

        nome_file = f"{CARTELLA_OUTPUT}/showcase_completo_{video_id}.mp4"

        if os.path.exists(nome_file):
            print("   [-] Video già scaricato, salto.")
            continue

        print(f"   [+] Scarico l'intero video (Risoluzione massima 720p)...")
        
        ydl_opts = {
            # IL TRUCCO È QUI: Scarica il miglior formato, ma con altezza massima di 720 pixel
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
            'outtmpl': nome_file,
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt' # Manteniamo il pass per i video vietati
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_dl:
                ydl_dl.download([video_url])
            print("   ✅ Download completo ottimizzato!")
        except Exception as e:
            print(f"   ❌ Errore durante il download: {e}")

if __name__ == "__main__":
    esegui_download_showcase()