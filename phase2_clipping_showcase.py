import yt_dlp
import json
import os
import re
import glob
from datetime import datetime

CARTELLA_OUTPUT = "clip_da_analizzare/showcases"

# Rimuove caratteri non consentiti nei nomi file (Windows/Linux/Mac)
def pulisci_nome_file(stringa):
    return re.sub(r'[\\/*?:"<>|]', "", stringa).replace(" ", "_")

def svuota_cartella(cartella):
    if not os.path.exists(cartella): return
    files = glob.glob(os.path.join(cartella, "*"))
    for f in files:
        try:
            os.remove(f)
        except Exception as e:
            print(f"   [Avviso] Impossibile eliminare {f}: {e}")

def esegui_download_showcase(file_json="risultati_fase1.json"):
    print("\n🔍 FASE 2: Download Showcase e Generazione JSON")
    if not os.path.exists(file_json): 
        return print("❌ File JSON mancante!")

    with open(file_json, 'r', encoding='utf-8') as f:
        dati = json.load(f)

    showcases = dati.get("showcases", [])
    if not showcases: 
        return print("Nessun showcase da processare.")

    os.makedirs(CARTELLA_OUTPUT, exist_ok=True)

    # 🧹 PULIZIA INIZIALE
    print(f"🧹 Pulizia della cartella {CARTELLA_OUTPUT} in corso...")
    svuota_cartella(CARTELLA_OUTPUT)

    for video in showcases:
        titolo_pulito = pulisci_nome_file(video['titolo'])
        url_video = video['url']
        
        nome_base = titolo_pulito
        percorso_clip = os.path.join(CARTELLA_OUTPUT, f"{nome_base}.mp4")
        percorso_json = os.path.join(CARTELLA_OUTPUT, f"{nome_base}.json")

        print(f"\n► Download Showcase: {video['titolo']}")
            
        ydl_opts = {
            'format': '18/worst', 
            'outtmpl': percorso_clip,
            'quiet': True, 
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_dl:
                info_dict = ydl_dl.extract_info(url_video, download=True)
                durata_video = info_dict.get('duration', 0)
            
            dati_metadati = {
                "dati_euristici_cpu": {
                    "video_originale": url_video,
                    "titolo_youtube": video['titolo'],
                    "inizio_sec": 0.0,
                    "finestra_temporale": {
                        "start": 0.0,
                        "end": float(durata_video)
                    },
                    "tipo_anomalia_sospetta": "video_showcase_integrale",
                    "fonte": "YouTube Showcase Engine",
                    "data_generazione": datetime.now().isoformat()
                },
                "diagnosi_semantica_ia": {}
            }
            
            with open(percorso_json, 'w', encoding='utf-8') as f:
                json.dump(dati_metadati, f, indent=4)
                
            print(f"   ✅ Salvato pacchetto IA: {nome_base}")
            
        except Exception as e:
            print(f"   ❌ Errore: {e}")

if __name__ == "__main__":
    esegui_download_showcase()