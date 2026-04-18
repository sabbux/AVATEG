import cv2
import os
import json
import pytesseract
import re
from difflib import SequenceMatcher # La nostra arma segreta per il confronto testi

# ⚠️ INSERISCI IL TUO PERCORSO DI TESSERACT
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\checc\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
CARTELLA_REPORT = "reports_vision"

def calcola_similarita(testo1, testo2, soglia_fuzzy=0.75):
    """
    Fuzzy Token Matching: Conta quante parole sono "simili" tra i due frame.
    Resiste sia alle parole cambiate di ordine (Bag-of-Words) 
    sia agli errori di battitura dell'OCR (Fuzzy Logic).
    """
    parole1 = testo1.split()
    parole2 = testo2.split()
    
    if len(parole1) == 0 or len(parole2) == 0:
        return 0
        
    parole_in_comune = 0
    # Copiamo la seconda lista per non "consumare" la stessa parola due volte
    parole2_copia = parole2.copy() 
    
    for p1 in parole1:
        for p2 in parole2_copia:
            # Calcoliamo la similarità tra LA SINGOLA PAROLA A e LA SINGOLA PAROLA B
            similarita_parola = SequenceMatcher(None, p1, p2).ratio()
            
            # Se la parola è uguale o ha solo 1-2 lettere sbagliate (75% simile)
            if similarita_parola >= soglia_fuzzy:
                parole_in_comune += 1
                parole2_copia.remove(p2) # Rimuoviamo la parola "accoppiata"
                break # Passiamo alla prossima parola del testo 1
                
    return parole_in_comune

def estrai_testo_schermo(frame):
    """La vista del Giudice: Binarizzazione, Upscaling e SANITIZZAZIONE del testo"""
    frame_grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame_ingrandito = cv2.resize(frame_grigio, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    _, frame_bn = cv2.threshold(frame_ingrandito, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    testo_estratto = pytesseract.image_to_string(frame_bn, config='--psm 11').upper()
    
    # --- FASE DI TEXT PRE-PROCESSING (Sanitizzazione) ---
    
    # 1. Rimuoviamo punteggiatura e simboli (teniamo solo lettere A-Z, numeri 0-9 e spazi)
    testo_alfanumerico = re.sub(r'[^A-Z0-9\s]', '', testo_estratto)
    
    # 2. Rimuoviamo le "paroline" di 1 o 2 lettere (che al 90% sono rumore grafico)
    # Es: "A Y S M 3 ROK TO" diventerà solo "ROK"
    parole_valide = [parola for parola in testo_alfanumerico.split() if len(parola) > 2]
    
    # 3. Riuniamo tutto in una stringa pulita
    testo_pulito = ' '.join(parole_valide)
    
    return testo_pulito

def analizza_softlock_video(video_path, intervallo_check_sec=5, secondi_allarme=30):
    print(f"\n🧩 Avvio Ricerca Softlock (Anchor System): {os.path.basename(video_path)}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    # --- NOVITÀ: Calcolo della Durata del Video e Soglia Dinamica ---
    totale_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps_originali = cap.get(cv2.CAP_PROP_FPS)
    if fps_originali <= 0: fps_originali = 30
    
    durata_video_sec = totale_frames / fps_originali
    
    # Se il video è corto, la soglia diventa l'80% della sua durata
    soglia_dinamica = min(secondi_allarme, durata_video_sec * 0.8)
    print(f"      [INFO] Durata video: {durata_video_sec:.1f}s | Soglia allarme impostata a: {soglia_dinamica:.1f}s")
    # ----------------------------------------------------------------
    
    frame_skip = int(fps_originali * intervallo_check_sec)
    frame_count = 0
    secondo_corrente = 0
    
    testo_ancora = "" 
    secondi_persistenza = 0
    strike_errori = 0  
    anomalie_rilevate = []

    while True:
        ret = cap.grab()
        if not ret: break
        
        frame_count += 1

        if frame_count % frame_skip == 0:
            ret, frame = cap.retrieve()
            if not ret: break
            
            secondo_corrente += intervallo_check_sec
            testo_attuale = estrai_testo_schermo(frame)
            
            if len(testo_attuale) < 10:
                strike_errori += 1
                if strike_errori > 1:
                    secondi_persistenza = 0
                    testo_ancora = ""
                continue
                
            if secondi_persistenza == 0 or testo_ancora == "":
                testo_ancora = testo_attuale
                strike_errori = 0 
                
            similarita = calcola_similarita(testo_attuale, testo_ancora)
            print(f"      [DEBUG] Sec {secondo_corrente} | Parole in comune: {similarita} | Testo: {testo_attuale[:40]}...")
            
            # --- NOVITÀ: SOGLIA ADATTIVA ---
            # Calcoliamo quante parole compongono la nostra Ancora
            lunghezza_ancora = len(testo_ancora.split())
            # Se l'interfaccia ha meno di 15 parole, basta 1 parola per salvarsi. Altrimenti ne servono 2.
            soglia_parole = 1 if lunghezza_ancora < 15 else 2
            
            if similarita >= soglia_parole:
                secondi_persistenza += intervallo_check_sec
                strike_errori = 0 
                print(f"      [⏳] Persistenza UI: {secondi_persistenza}s (Soglia richiesta: {soglia_parole})")
                
                # Usiamo la soglia_dinamica invece di secondi_allarme!
                if secondi_persistenza >= soglia_dinamica:
                    print(f"   🚨 SOFTLOCK CONFERMATO AL SECONDO {secondo_corrente}!")
                    anomalie_rilevate.append({
                        "inizio_sec": secondo_corrente - secondi_persistenza,
                        "fine_sec": secondo_corrente,
                        "durata_sec": secondi_persistenza,
                        "tipo": "Softlock (UI Persistente)",
                        "testo": testo_ancora[:50]
                    })
                    secondi_persistenza = 0 
                    testo_ancora = ""
            else:
                strike_errori += 1
                print(f"      [⚠️] Attenzione: Calo di lettura (Strike {strike_errori}/2)")
                
                if strike_errori >= 2:
                    print(f"      [❌] UI sparita definitivamente. Azzero il timer.")
                    secondi_persistenza = 0
                    testo_ancora = testo_attuale
                    strike_errori = 0

    cap.release()
    print("   ✅ Analisi Softlock terminata.")
    return anomalie_rilevate

def esegui_batch_softlock():
    print("👁️ FASE 3 (Modulo Avanzato): Rilevamento Softlock Logici (Lettura UI)")
    os.makedirs(CARTELLA_REPORT, exist_ok=True)
    
    # Puntiamo alla cartella dove abbiamo i video critici per i test iniziali
    cartelle_input = ["clip_generate/showcase"]
    report_totale = {}

    for cartella in cartelle_input:
        if not os.path.exists(cartella): continue
        video_files = [f for f in os.listdir(cartella) if f.endswith('.mp4')]
        
        for file in video_files:
            video_path = os.path.join(cartella, file)
            # Leggiamo ogni 5 secondi, suoniamo l'allarme se il testo è fisso per 30 secondi
            risultati = analizza_softlock_video(video_path, intervallo_check_sec=5, secondi_allarme=30)
            
            if risultati:
                report_totale[file] = risultati

    percorso_json = os.path.join(CARTELLA_REPORT, 'softlock_report.json')
    with open(percorso_json, 'w', encoding='utf-8') as f:
        json.dump(report_totale, f, indent=4)
    
    print(f"\n✅ Pipeline Softlock Completata. Report: {percorso_json}")

if __name__ == "__main__":
    esegui_batch_softlock()