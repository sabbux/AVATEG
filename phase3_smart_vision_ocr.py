import subprocess
import cv2
from thefuzz import fuzz
import numpy as np
import os
import json
import pytesseract
import re

# ⚠️ Percorso di Tesseract sul tuo PC
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\checc\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
CARTELLA_REPORT = "reports_vision"
CARTELLA_ANOMALIE = "anomalie_rilevate" # 💡 Nuova cartella per le clip tagliate

def estrai_micro_clip(video_originale, inizio_sec, durata_sec, output_path, margine_sec=3.0):
    start_time = max(0.0, inizio_sec - margine_sec)
    clip_duration = margine_sec + durata_sec + margine_sec
    comando = [
        "ffmpeg", "-y", "-ss", str(start_time), "-i", video_originale,
        "-t", str(clip_duration), "-c", "copy", output_path
    ]
    subprocess.run(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def e_schermata_nera(frame, soglia_luminosita=15):
    luminosita_media = np.mean(frame)
    if luminosita_media < soglia_luminosita:
        print(f"      [FILTRO NERO] Luminosità ({luminosita_media:.1f}) sotto soglia. Transizione ignorata.")
        return True
    return False

def e_testo_spazzatura(testo_pulito):
    if len(testo_pulito) < 3: 
        return True 
        
    lettere = len(re.findall(r'[A-Z0-9]', testo_pulito))
    simboli = len(re.findall(r'[^A-Z0-9\s]', testo_pulito))
    
    if simboli > lettere:
        print(f"      [FILTRO GIBBERISH] Trovati {simboli} simboli su {lettere} lettere. È un'immagine di caricamento, la ignoro.")
        return True
        
    return False

def e_artwork_complesso(frame_grigio):
    bordi = cv2.Canny(frame_grigio, 100, 200)
    densita_bordi = np.count_nonzero(bordi) / bordi.size
    
    if densita_bordi > 0.06:
        print(f"      [FILTRO CANNY] Densità bordi troppo alta ({densita_bordi:.2f}). È un artwork/caricamento, non un menù.")
        return True
        
    return False

def valida_falso_positivo_ocr(frame):
    if e_schermata_nera(frame):
        return True 

    frame_grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if e_artwork_complesso(frame_grigio): return True
    
    altezza, larghezza = frame_grigio.shape
    margine_y = int(altezza * 0.15)
    margine_x = int(larghezza * 0.15)
    roi_grigio = frame_grigio[margine_y:altezza-margine_y, margine_x:larghezza-margine_x]
    
    frame_ingrandito = cv2.resize(roi_grigio, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    _, frame_bn = cv2.threshold(frame_ingrandito, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    testo_estratto = pytesseract.image_to_string(frame_bn, config='--psm 11').upper()
    testo_pulito = testo_estratto.replace('\n', ' ').strip()

    if e_testo_spazzatura(testo_pulito): return True
    
    keyword_menu = [
        "RESUME", "INVENTORY", "MAP", "CHARACTER", "JOURNAL", "SETTINGS", 
        "EXIT", "FLATLINED", "STREET CRED", "LOAD", "CHECKPOINT", "SAVED GAME", "LOAD GAME",
        "MISSION FAILED", "MAIN MENU", "RETURN TO", "PAUSE", "OPTIONS", "GAME PAUSED", "ADVANCED OPTIONS",
        "CONTINUE", "RESTART", "GAME OVER", "LOADING", "SAVE", "NEW GAME", "QUIT", "BACK TO MENU"
    ]
    
    for parola in keyword_menu:
        score = fuzz.partial_ratio(parola, testo_pulito)
        if score >= 80:
            print(f"      [GIUDICE FUZZY] Trovato '{parola}' (Score: {score}%). Falso allarme annullato!")
            return True 
            
    return False

def controllo_ocr_periferico(frame):
    frame_grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    altezza, larghezza = frame_grigio.shape
    
    my = int(altezza * 0.15)
    mx = int(larghezza * 0.25)
    
    top_left = frame_grigio[0:my, 0:mx]
    top_right = frame_grigio[0:my, larghezza-mx:larghezza]
    bottom_left = frame_grigio[altezza-my:altezza, 0:mx]
    bottom_right = frame_grigio[altezza-my:altezza, larghezza-mx:larghezza]
    
    stack_periferico = cv2.vconcat([top_left, top_right, bottom_left, bottom_right])
    stack_zoom = cv2.resize(stack_periferico, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    _, stack_bn = cv2.threshold(stack_zoom, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    testo_periferico = pytesseract.image_to_string(stack_bn, config='--psm 11').upper()
    
    keyword_angoli = [
        "SAVE", "SAVING", "LOAD", "LOADING", "PRESS", "CONTINUE", 
        "SKIP", "WAIT", "ENTER", "BACK", "MENU", "OPTIONS", 
        "A TO", "X TO", "ANY BUTTON"
    ]
    
    for kw in keyword_angoli:
        if kw in testo_periferico:
            print(f"      [PERIPHERAL OCR] Intercettata UI periferica nascosta: '{kw}'. Falso Positivo eluso!")
            return True 
            
    return False    

def analizza_freeze_video(video_path, campionamento_fps=10, soglia_movimento=0.026, secondi_allarme=0.3):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("   ❌ Errore: Impossibile aprire il video.")
        return None

    fps_originali = cap.get(cv2.CAP_PROP_FPS)
    if fps_originali <= 0: fps_originali = 30
    
    frame_skip = max(1, int(fps_originali / campionamento_fps))
    durata_step_sec = frame_skip / fps_originali 
    
    frame_precedente_grigio = None
    tempo_consecutivo_bloccato = 0.0 
    frame_congelato_da_analizzare = None 
    anomalie_rilevate = []
    
    picco_movimento_recente = 0.0
    transizione_brusca_attiva = False
    
    frame_count = 0
    secondo_corrente = 0.0

    while True:
        ret = cap.grab()
        if not ret: break
        
        frame_count += 1
        secondo_corrente = frame_count / fps_originali

        if frame_count % frame_skip == 0:
            ret, frame = cap.retrieve()
            if not ret: break

            frame_grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame_sfocato = cv2.GaussianBlur(frame_grigio, (5, 5), 0)

            if frame_precedente_grigio is not None:
                differenza_pixel = cv2.absdiff(frame_precedente_grigio, frame_sfocato)
                pixel_cambiati = np.count_nonzero(differenza_pixel > 15)
                percentuale_cambiamento = (pixel_cambiati / frame_sfocato.size) * 100

                if percentuale_cambiamento < soglia_movimento:
                    
                    _, thresh = cv2.threshold(differenza_pixel, 15, 255, cv2.THRESH_BINARY)
                    punti_in_movimento = cv2.findNonZero(thresh)
                    
                    is_spinner = False
                    if punti_in_movimento is not None:
                        x, y, w, h = cv2.boundingRect(punti_in_movimento)
                        area_movimento = w * h
                        area_schermo = frame_sfocato.shape[0] * frame_sfocato.shape[1]
                        
                        if 0 < area_movimento < (area_schermo * 0.05):
                            is_spinner = True
                    
                    if is_spinner:
                        tempo_consecutivo_bloccato = 0.0
                        frame_congelato_da_analizzare = None
                        transizione_brusca_attiva = False
                    else:
                        if tempo_consecutivo_bloccato == 0.0:
                            if picco_movimento_recente > 60.0:
                                transizione_brusca_attiva = True
                                print(f"      [FILTRO TRANSIZIONE] Cambio scena totale rilevato ({picco_movimento_recente:.1f}%).")
                            else:
                                transizione_brusca_attiva = False

                        tempo_consecutivo_bloccato += durata_step_sec
                        
                        if frame_congelato_da_analizzare is None:
                            frame_congelato_da_analizzare = frame.copy()
                
                else:
                    picco_movimento_recente = percentuale_cambiamento

                    if tempo_consecutivo_bloccato >= secondi_allarme:
                        inizio_blocco = secondo_corrente - tempo_consecutivo_bloccato
                        
                        if transizione_brusca_attiva:
                            print(f"   [SCARTATO] Blocco di {tempo_consecutivo_bloccato:.1f}s era un'apertura menù/cutscene.")
                        else:
                            print(f"   [?] Possibile freeze da sec {inizio_blocco:.1f} a {secondo_corrente:.1f}. Chiamo l'OCR...")
                            
                            is_menu = valida_falso_positivo_ocr(frame_congelato_da_analizzare)
                            
                            if not is_menu:
                                print("   [?] OCR Globale eluso. Avvio scansione Periferica...")
                                is_menu_nascosto = controllo_ocr_periferico(frame_congelato_da_analizzare)
                                
                                if not is_menu_nascosto:
                                    print(f"   🚨 ALLARME CONFERMATO: Freeze reale di {tempo_consecutivo_bloccato:.1f}s!")
                                    
                                    # 💡 --- INIZIO INTEGRAZIONE ESPORTAZIONE CLIP ---
                                    # Ricaviamo il nome del video pulito (es. "ok9TV-lZyJk")
                                    nome_video_pulito = os.path.basename(video_path).split('.')[0]
                                    nome_base = f"freeze_{nome_video_pulito}_{inizio_blocco:.1f}s"
                                    
                                    path_clip = os.path.join(CARTELLA_ANOMALIE, f"{nome_base}.mp4")
                                    path_meta = os.path.join(CARTELLA_ANOMALIE, f"{nome_base}.json")

                                    # 1. Tagliamo il video e lo salviamo su disco
                                    estrai_micro_clip(video_path, inizio_blocco, tempo_consecutivo_bloccato, path_clip)

                                    # 2. Creiamo il payload JSON per istruire l'LMM
                                    metadati = {
                                        "video_originale": video_path,
                                        "inizio_sec": inizio_blocco,
                                        "durata_sec": tempo_consecutivo_bloccato
                                    }
                                    with open(path_meta, "w", encoding='utf-8') as f:
                                        json.dump(metadati, f, indent=4)
                                        
                                    print(f"      ✂️ Clip e metadati esportati in '{CARTELLA_ANOMALIE}/'")
                                    # 💡 --- FINE INTEGRAZIONE ESPORTAZIONE CLIP ---

                                    anomalie_rilevate.append({
                                        "inizio_sec": inizio_blocco,
                                        "fine_sec": secondo_corrente,
                                        "durata_sec": tempo_consecutivo_bloccato
                                    })
                    
                    tempo_consecutivo_bloccato = 0.0
                    frame_congelato_da_analizzare = None
                    transizione_brusca_attiva = False

            frame_precedente_grigio = frame_sfocato

    cap.release()
    return anomalie_rilevate

def esegui_batch_vision():
    print("👁️ FASE 3: Batch Computer Vision - GOLDEN MASTER (Rilevamento Freeze SMART + Filtri AVATEG)")
    
    # Crea le cartelle necessarie prima di iniziare
    os.makedirs(CARTELLA_REPORT, exist_ok=True)
    os.makedirs(CARTELLA_ANOMALIE, exist_ok=True) 
    
    cartelle_input = ["benchmark_phase3/dataset_haste"]
    report_totale = {}

    for cartella in cartelle_input:
        if not os.path.exists(cartella): continue
        
        video_files = [f for f in os.listdir(cartella) if f.endswith('.mp4')]
        
        for file in video_files:
            video_path = os.path.join(cartella, file)
            print(f"\n► Analizzo: {file}")
            
            risultati = analizza_freeze_video(video_path, campionamento_fps=10, soglia_movimento=0.026, secondi_allarme=0.3)
            
            if risultati is None: continue
            if risultati:
                report_totale[file] = risultati
            else:
                print("   ✅ Nessun freeze reale rilevato.")

    percorso_json = os.path.join(CARTELLA_REPORT, 'freeze_smart_report.json')
    with open(percorso_json, 'w', encoding='utf-8') as f:
        json.dump(report_totale, f, indent=4)
    
    print(f"\n✅ Pipeline Completata. Report esportato in: {percorso_json}")
    print(f"🎬 Le clip tagliate per l'Intelligenza Artificiale ti aspettano nella cartella: {CARTELLA_ANOMALIE}/")

if __name__ == "__main__":
    esegui_batch_vision()