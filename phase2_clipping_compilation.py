import yt_dlp
import json
import os
import re
import glob
from datetime import datetime
from scenedetect import detect, AdaptiveDetector, split_video_ffmpeg, FrameTimecode

CARTELLA_OUTPUT = "clip_da_analizzare/compilations"

# Rimuove caratteri non consentiti nei nomi file (Windows/Linux/Mac)
def pulisci_nome(s):
    return re.sub(r'[\\/*?:"<>|]', "", s).replace(" ", "_")[:30]

def svuota_cartella(cartella):
    if not os.path.exists(cartella): return
    files = glob.glob(os.path.join(cartella, "*"))
    for f in files:
        try:
            os.remove(f)
        except Exception as e:
            print(f"   [Avviso] Impossibile eliminare {f}: {e}")

def esegui_clipping_compilation(file_json="risultati_fase1.json"):
    print("🎞️ FASE 2: Scene Detection ADATTIVA e Generazione JSON")
    if not os.path.exists(file_json): 
        return print("❌ File risultati_fase1.json non trovato!")
    
    with open(file_json, 'r', encoding='utf-8') as f:
        dati = json.load(f)

    compilations = dati.get("compilations", [])
    if not compilations: return

    os.makedirs(CARTELLA_OUTPUT, exist_ok=True)
    
    # 🧹 PULIZIA INIZIALE
    print(f"🧹 Pulizia della cartella {CARTELLA_OUTPUT} in corso...")
    svuota_cartella(CARTELLA_OUTPUT)

    for video in compilations:
        titolo_legge = pulisci_nome(video['titolo'])
        url_video = video['url']
        file_temp = f"{CARTELLA_OUTPUT}/temp_{video['video_id']}.mp4"
        
        print(f"\n► Analizzo Compilation: {video['titolo']}")
        ydl_opts = {'format': '18/worst', 'outtmpl': file_temp, 'quiet': True, 'no_warnings': True}
        
        try:
            if not os.path.exists(file_temp):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: 
                    ydl.download([url_video])

            # Prevenzione contro le scene caotiche (min_scene_len=450 equivale a 15s a 30fps)
            detector = AdaptiveDetector(adaptive_threshold=5.0, min_scene_len=450)
            scene_list = detect(file_temp, detector)

            # --- RILEVAZIONE, DEDUPLICAZIONE E PRE-ROLL ---
            scene_uniche = []
            ultimo_start = -1
            
            for start, end in scene_list:
                start_sec = start.get_seconds()
                durata = end.get_seconds() - start_sec

                 # 1. Filtro duplicati
                if abs(start_sec - ultimo_start) < 5.0: continue

                 # 2. Filtro durata
                if 10.0 <= durata <= 60.0:
                    fps = start.framerate
                    start_con_contesto = max(0.0, start_sec - 4.0) 
                    nuovo_start = FrameTimecode(timecode=start_con_contesto, fps=fps)
                    scene_uniche.append((nuovo_start, end))
                    ultimo_start = start_sec

            if scene_uniche:
                print(f"   -> Individuate {len(scene_uniche)} clip. Esporto video e JSON...")
                
                template_output = f"{CARTELLA_OUTPUT}/{titolo_legge}_SC$SCENE_NUMBER.mp4"
                
                split_video_ffmpeg(
                    file_temp, 
                    scene_uniche, 
                    output_file_template=template_output,
                    show_progress=False
                )
                
                for i, (start_tc, end_tc) in enumerate(scene_uniche, start=1):
                    num_scena = f"{i:03d}" 
                    nome_base = f"{titolo_legge}_SC{num_scena}"
                    percorso_json = os.path.join(CARTELLA_OUTPUT, f"{nome_base}.json")
                    
                    start_sec_val = start_tc.get_seconds()
                    end_sec_val = end_tc.get_seconds()
                    
                    dati_metadati = {
                        "dati_euristici_cpu": {
                            "video_originale": url_video,
                            "titolo_youtube": video['titolo'],
                            "inizio_sec": start_sec_val,
                            "finestra_temporale": {
                                "start": start_sec_val,
                                "end": end_sec_val
                            },
                            "tipo_anomalia_sospetta": "rilevamento_visivo_compilation",
                            "fonte": "YouTube SceneDetect Engine",
                            "data_generazione": datetime.now().isoformat()
                        },
                        "diagnosi_semantica_ia": {}
                    }
                    
                    with open(percorso_json, 'w', encoding='utf-8') as f:
                        json.dump(dati_metadati, f, indent=4)
                        
            else:
                print("   [-] Nessuna scena soddisfa i criteri.")

        except Exception as e:
            print(f"   ❌ Errore: {e}")
        finally:
            if os.path.exists(file_temp): os.remove(file_temp)

if __name__ == "__main__":
    esegui_clipping_compilation()