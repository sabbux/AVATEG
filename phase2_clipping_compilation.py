import yt_dlp
import json
import os
import re
from scenedetect import detect, AdaptiveDetector, split_video_ffmpeg, FrameTimecode # Aggiunto FrameTimecode

CARTELLA_OUTPUT = "clip_generate/compilation"

def pulisci_nome(s):
    return re.sub(r'[\\/*?:"<>|]', "", s).replace(" ", "_")[:30]

def esegui_clipping_compilation(file_json="risultati_fase1.json"):
    print("🎞️ FASE 2: Scene Detection ADATTIVA (High Inertia + Pre-Roll)")
    if not os.path.exists(file_json): 
        return print("File risultati_fase1.json non trovato!")
    
    with open(file_json, 'r', encoding='utf-8') as f:
        dati = json.load(f)

    compilations = dati.get("compilations", [])
    if not compilations: return

    os.makedirs(CARTELLA_OUTPUT, exist_ok=True)

    for video in compilations:
        titolo_legge = pulisci_nome(video['titolo'])
        file_temp = f"{CARTELLA_OUTPUT}/temp_{video['video_id']}.mp4"
        
        print(f"\n► Analizzo: {video['titolo']}")
        ydl_opts = {'format': '18/worst', 'outtmpl': file_temp, 'quiet': True}
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: 
                ydl.download([video['url']])
            
            detector = AdaptiveDetector(adaptive_threshold=5.0, min_scene_len=450)
            scene_list = detect(file_temp, detector)
            
            # --- RILEVAZIONE, DEDUPLICAZIONE E PRE-ROLL ---
            scene_uniche = []
            ultimo_start = -1
            
            for start, end in scene_list:
                start_sec = start.get_seconds()
                durata = end.get_seconds() - start_sec
                
                # 1. Filtro duplicati
                if abs(start_sec - ultimo_start) < 5.0:
                    continue
                
                # 2. Filtro durata
                if 10.0 <= durata <= 60.0:
                    # 3. IL PRE-ROLL: Sottraiamo 4 secondi per recuperare il contesto
                    fps = start.framerate
                    # Usiamo max(0.0, ...) per evitare di andare in negativo se il bug è all'inizio del video
                    start_con_contesto = max(0.0, start_sec - 4.0) 
                    
                    # Creiamo il nuovo timestamp modificato
                    nuovo_start = FrameTimecode(timecode=start_con_contesto, fps=fps)
                    
                    scene_uniche.append((nuovo_start, end))
                    ultimo_start = start_sec

            if scene_uniche:
                print(f"   -> Individuate {len(scene_uniche)} clip (con 4s di contesto). Esporto...")
                split_video_ffmpeg(
                    file_temp, 
                    scene_uniche, 
                    output_file_template=f"{CARTELLA_OUTPUT}/{titolo_legge}_SC$SCENE_NUMBER.mp4",
                    show_progress=False
                )
            else:
                print("   [-] Nessuna scena soddisfa i criteri.")

        except Exception as e:
            print(f"   ❌ Errore: {e}")
        finally:
            if os.path.exists(file_temp): os.remove(file_temp)

if __name__ == "__main__":
    esegui_clipping_compilation()