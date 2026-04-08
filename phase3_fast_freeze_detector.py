import cv2
import numpy as np
import os
import json

CARTELLA_REPORT = "reports_vision"

def analizza_freeze_video(video_path, campionamento_fps=1, soglia_movimento=0.10, secondi_allarme=2):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("   ❌ Errore: Impossibile aprire il video.")
        return None

    fps_originali = cap.get(cv2.CAP_PROP_FPS)
    if fps_originali <= 0: fps_originali = 30
    
    frame_skip = int(fps_originali / campionamento_fps)
    
    frame_precedente_grigio = None
    secondi_consecutivi_bloccati = 0
    anomalie_rilevate = []
    
    frame_count = 0
    secondo_corrente = 0

    print("   [!] Avvio telemetria di movimento...")

    while True:
        ret = cap.grab()
        if not ret: break
        
        frame_count += 1

        if frame_count % frame_skip == 0:
            ret, frame = cap.retrieve()
            if not ret: break

            frame_grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Blur ridotto drasticamente per i video a 360p
            frame_grigio = cv2.GaussianBlur(frame_grigio, (5, 5), 0)

            if frame_precedente_grigio is not None:
                differenza_pixel = cv2.absdiff(frame_precedente_grigio, frame_grigio)
                
                # Sensibilità aumentata per beccare i dialoghi (> 15 invece di > 25)
                pixel_cambiati = np.count_nonzero(differenza_pixel > 15)
                totale_pixel = frame_grigio.size
                percentuale_cambiamento = (pixel_cambiati / totale_pixel) * 100

                # TELEMETRIA IN TEMPO REALE:
                # print(f"      Sec {secondo_corrente}: Movimento = {percentuale_cambiamento:.3f}%")

                if percentuale_cambiamento < soglia_movimento:
                    secondi_consecutivi_bloccati += 1
                    print(f"      [BLOCCO] Sec {secondo_corrente}: Movimento = {percentuale_cambiamento:.3f}%")
                else:
                    if secondi_consecutivi_bloccati >= secondi_allarme:
                        anomalie_rilevate.append({
                            "inizio_sec": secondo_corrente - secondi_consecutivi_bloccati,
                            "fine_sec": secondo_corrente,
                            "durata_sec": secondi_consecutivi_bloccati
                        })
                        print(f"      [!] FREEZE CONFERMATO DI {secondi_consecutivi_bloccati}s")
                    
                    secondi_consecutivi_bloccati = 0
                    # Togli il cancelletto (#) dalla riga qui sotto se vuoi vedere i dati di quando è fluido
                    print(f"      [Fluido] Sec {secondo_corrente}: Movimento = {percentuale_cambiamento:.3f}%")

            frame_precedente_grigio = frame_grigio
            secondo_corrente += 1

    cap.release()

    if secondi_consecutivi_bloccati >= secondi_allarme:
        anomalie_rilevate.append({
            "inizio_sec": secondo_corrente - secondi_consecutivi_bloccati,
            "fine_sec": secondo_corrente,
            "durata_sec": secondi_consecutivi_bloccati
        })

    return anomalie_rilevate

def esegui_batch_vision():
    print("👁️ FASE 3: Batch Computer Vision (Rilevamento Freeze)")
    os.makedirs(CARTELLA_REPORT, exist_ok=True)
    
    # Definisci quali cartelle vuoi scansionare
    cartelle_input = ["clip_generate/compilation", "clip_generate/gameplay", "clip_generate/showcase"]
    report_totale = {}

    for cartella in cartelle_input:
        if not os.path.exists(cartella): continue
        
        video_files = [f for f in os.listdir(cartella) if f.endswith('.mp4')]
        
        for file in video_files:
            video_path = os.path.join(cartella, file)
            print(f"\n► Analizzo: {file}")
            
            # PARAMETRI AGGIORNATI PER FREEZE BREVI E VIDEO COMPRESSI:
            # - soglia_movimento=1.5: Tolleriamo fino all'1.5% di pixel "sfrigolanti" per colpa di YouTube
            # - secondi_allarme=2: Vogliamo che suoni l'allarme anche per micro-blocchi di 2 secondi
            risultati = analizza_freeze_video(
                video_path, 
                campionamento_fps=1, 
                soglia_movimento=1.5, 
                secondi_allarme=2
            )
            
            if risultati is None: continue
            
            report_totale[file] = risultati
            
            if risultati:
                print(f"   🚨 Trovati {len(risultati)} freeze!")
                for r in risultati:
                    print(f"      - Blocco di {r['durata_sec']}s (da {r['inizio_sec']}s a {r['fine_sec']}s)")
            else:
                print("   ✅ Immagine fluida, nessun freeze rilevato.")

    # Salvataggio su database locale
    percorso_json = os.path.join(CARTELLA_REPORT, 'freeze_report.json')
    with open(percorso_json, 'w', encoding='utf-8') as f:
        json.dump(report_totale, f, indent=4)
    
    print(f"\n✅ Analisi completata. Dati estratti in: {percorso_json}")

if __name__ == "__main__":
    esegui_batch_vision()