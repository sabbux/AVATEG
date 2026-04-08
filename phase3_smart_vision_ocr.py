import cv2
import numpy as np
import os
import json
import pytesseract

# ⚠️ Percorso di Tesseract sul tuo PC
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\checc\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
CARTELLA_REPORT = "reports_vision"

def valida_falso_positivo_ocr(frame):
    """Il Giudice V3: Upscaling per video a bassa risoluzione (360p)."""
    frame_grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # L'ARMA SEGRETA: Ingrandiamo l'immagine del 300% prima di leggerla
    # INTER_CUBIC calcola i pixel mancanti e rende i bordi delle lettere netti
    frame_ingrandito = cv2.resize(frame_grigio, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    
    # Applichiamo il bianco e nero sull'immagine gigante
    _, frame_bn = cv2.threshold(frame_ingrandito, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Lettura
    testo_estratto = pytesseract.image_to_string(frame_bn, config='--psm 11').upper()
    
    # DEBUG per vedere cosa legge ora che l'immagine è enorme
    testo_pulito = testo_estratto.replace('\n', ' ').strip()
    print(f"      [DEBUG OCR] Il Giudice legge: {testo_pulito[:100]}")
    
    keyword_menu = [
        "RESUME", "INVENTORY", "MAP", "CHARACTER", "JOURNAL", "SETTINGS", 
        "EXIT", "FLATLINED", "LOAD", "CHECKPOINT", "SAVED GAME", 
        "MISSION FAILED", "MAIN MENU", "RETURN TO", "PAUSE", "OPTIONS",
        "CONTINUE", "RESTART", "GAME OVER", "LOADING", "SAVE", "NEW GAME", "QUIT", "BACK TO MENU"
    ]
    
    for parola in keyword_menu:
        if parola in testo_estratto:
            print(f"      [GIUDICE OCR] Trovata scritta '{parola}'. Falso allarme annullato!")
            return True 
            
    return False

def analizza_freeze_video(video_path, campionamento_fps=1, soglia_movimento=1.0, secondi_allarme=2):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("   ❌ Errore: Impossibile aprire il video.")
        return None

    fps_originali = cap.get(cv2.CAP_PROP_FPS)
    if fps_originali <= 0: fps_originali = 30
    frame_skip = int(fps_originali / campionamento_fps)
    
    frame_precedente_grigio = None
    secondi_consecutivi_bloccati = 0
    anomalie_rilevate = [] # La lista che popolerà il nostro JSON
    
    frame_count = 0
    secondo_corrente = 0

    while True:
        ret = cap.grab()
        if not ret: break
        
        frame_count += 1

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
                    secondi_consecutivi_bloccati += 1
                else:
                    if secondi_consecutivi_bloccati >= secondi_allarme:
                        print(f"   [?] Possibile freeze da sec {secondo_corrente - secondi_consecutivi_bloccati} a {secondo_corrente}. Chiamo l'OCR...")
                        
                        is_menu = valida_falso_positivo_ocr(frame)
                        
                        # Salviamo il freeze SOLO se l'OCR conferma che non è un menù
                        if not is_menu:
                            print(f"   🚨 ALLARME CONFERMATO: Freeze reale di {secondi_consecutivi_bloccati}s!")
                            anomalie_rilevate.append({
                                "inizio_sec": secondo_corrente - secondi_consecutivi_bloccati,
                                "fine_sec": secondo_corrente,
                                "durata_sec": secondi_consecutivi_bloccati
                            })
                    
                    secondi_consecutivi_bloccati = 0

            frame_precedente_grigio = frame_sfocato
            secondo_corrente += 1

    cap.release()

    # Controllo di fine video
    if secondi_consecutivi_bloccati >= secondi_allarme:
        # Passiamo l'ultimo frame letto (non possiamo estrarlo se il video è finito, ma ci accontentiamo)
        anomalie_rilevate.append({
            "inizio_sec": secondo_corrente - secondi_consecutivi_bloccati,
            "fine_sec": secondo_corrente,
            "durata_sec": secondi_consecutivi_bloccati
        })

    return anomalie_rilevate

def esegui_batch_vision():
    print("👁️ FASE 3: Batch Computer Vision (Rilevamento Freeze SMART + OCR)")
    os.makedirs(CARTELLA_REPORT, exist_ok=True)
    
    cartelle_input = ["clip_generate/compilation", "clip_generate/gameplay", "clip_generate/showcase"]
    report_totale = {}

    for cartella in cartelle_input:
        if not os.path.exists(cartella): continue
        
        video_files = [f for f in os.listdir(cartella) if f.endswith('.mp4')]
        
        for file in video_files:
            video_path = os.path.join(cartella, file)
            print(f"\n► Analizzo: {file}")
            
            risultati = analizza_freeze_video(video_path, campionamento_fps=1, soglia_movimento=1.5, secondi_allarme=2)
            
            if risultati is None: continue
            if risultati:
                report_totale[file] = risultati
            else:
                print("   ✅ Nessun freeze reale rilevato.")

    percorso_json = os.path.join(CARTELLA_REPORT, 'freeze_smart_report.json')
    with open(percorso_json, 'w', encoding='utf-8') as f:
        json.dump(report_totale, f, indent=4)
    
    print(f"\n✅ Pipeline Completata. Report esportato in: {percorso_json}")

if __name__ == "__main__":
    esegui_batch_vision()