import yt_dlp
import json
import os
from scenedetect import detect, ContentDetector, split_video_ffmpeg

CARTELLA_OUTPUT = "clip_generate/compilation"

def esegui_clipping_compilation(file_json="risultati_fase1.json"):
    print("🎞️ FASE 2: Scene Detection per Compilation")
    if not os.path.exists(file_json): return print("File JSON mancante!")
    
    with open(file_json, 'r', encoding='utf-8') as f:
        dati = json.load(f)
        
    compilations = dati.get("compilations", [])
    if not compilations: return print("Nessuna compilation da processare nel JSON.")

    os.makedirs(CARTELLA_OUTPUT, exist_ok=True)

    for video in compilations:
        print(f"\n► Elaboro Compilation: {video['titolo']}")
        file_temp = f"{CARTELLA_OUTPUT}/temp_{video['video_id']}.mp4"
        
        print("   -> Scaricamento video a bassa risoluzione (144p/360p)...")
        ydl_opts = {'format': 'worst[ext=mp4]', 'outtmpl': file_temp, 'quiet': True, 'no_warnings': True}
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([video['url']])
            
            print("   -> Ricerca cambi di scena...")
            scene_list = detect(file_temp, ContentDetector(threshold=27.0))
            
            scene_valide = [s for s in scene_list if 3.0 <= (s[1].get_seconds() - s[0].get_seconds()) <= 60.0]
            print(f"   [!] Trovate {len(scene_valide)} clip di gameplay valide.")
            
            if scene_valide:
                print("   -> Taglio fisico con FFmpeg in corso...")
                split_video_ffmpeg(
                    file_temp, 
                    scene_valide, 
                    output_file_template=f"{CARTELLA_OUTPUT}/comp_{video['video_id']}_scene_$SCENE_NUMBER.mp4",
                    show_progress=False
                )
        except Exception as e:
            print(f"   ❌ Errore durante l'elaborazione: {e}")
        finally:
            # Pulizia per non intasare il disco
            if os.path.exists(file_temp):
                os.remove(file_temp)
                print("   -> File temporaneo rimosso.")

if __name__ == "__main__":
    esegui_clipping_compilation()