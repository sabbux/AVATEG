import cv2
import numpy as np
import pandas as pd
import os
from collections import deque

def estrai_features_batch(cartella_video, csv_output_path, campionamento_fps=10):
    # Cerca i video nella cartella specifica
    video_files = [f for f in os.listdir(cartella_video) if f.endswith(('.mp4', '.mkv', '.avi'))]
    
    if not video_files:
        print(f"❌ Nessun video trovato in '{cartella_video}'. Verifica i percorsi.")
        return

    saliency_algo = cv2.saliency.StaticSaliencySpectralResidual_create()
    dati_estratti = [] 

    print(f"🚀 Avvio estrazione features su {len(video_files)} video. Attendere...\n")

    for file_video in video_files:
        video_path = os.path.join(cartella_video, file_video)
        print(f"► Estrazione in corso da: {file_video}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"   ⚠️ Impossibile aprire {file_video}. Salto.")
            continue
        
        fps_originali = cap.get(cv2.CAP_PROP_FPS)
        if fps_originali <= 0: fps_originali = 30
        frame_skip = max(1, int(fps_originali / campionamento_fps))
        
        frame_precedente_grigio = None
        buffer_movimento = deque(maxlen=5) 
        frame_count = 0

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
                    # 1. AbsDiff (Movimento Globale)
                    differenza_pixel = cv2.absdiff(frame_precedente_grigio, frame_sfocato)
                    pixel_cambiati = np.count_nonzero(differenza_pixel > 15)
                    percentuale_diff = (pixel_cambiati / frame_sfocato.size) * 100
                    buffer_movimento.append(percentuale_diff)
                    
                    # 2. Geometria (Area Blob)
                    _, diff_binaria = cv2.threshold(differenza_pixel, 15, 255, cv2.THRESH_BINARY)
                    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(diff_binaria, connectivity=8)
                    area_max_blob = 0
                    if num_labels > 1:
                        area_max_blob = np.max(stats[1:, cv2.CC_STAT_AREA])

                    # 3. Salienza (Attenzione HUD)
                    success, mappa_salienza = saliency_algo.computeSaliency(frame)
                    salienza_media = np.mean(mappa_salienza) if success else 0.0

                    # 4. Cinematica (Varianza Temporale)
                    varianza_temporale = np.var(buffer_movimento) if len(buffer_movimento) > 1 else 0.0

                    # Salvataggio Riga
                    dati_estratti.append({
                        "Nome_Video": file_video, 
                        "Secondo": round(secondo_corrente, 2),
                        "AbsDiff_Perc": round(percentuale_diff, 4),
                        "Max_Blob_Area": area_max_blob,
                        "Saliency_Mean": round(salienza_media, 4),
                        "Temp_Variance": round(varianza_temporale, 4),
                        "Label_Freeze": 0  # Inizializzato a 0. Modificherai tu i freeze.
                    })

                frame_precedente_grigio = frame_sfocato

        cap.release()
        print(f"   ✓ Completato: {file_video}")

    # Esportazione CSV
    df = pd.DataFrame(dati_estratti)
    df.to_csv(csv_output_path, index=False)
    print(f"\n✅ ESTRAZIONE GLOBALE COMPLETATA!")
    print(f"   Dataset salvato in '{csv_output_path}' ({len(df)} righe generate).")

# --- PATH RELATIVI DINAMICI ---
# Punta direttamente alla cartella nidificata del tuo progetto
cartella_input = os.path.join("benchmark_phase3", "dataset_haste") 
file_output_csv = "dataset_haste_features.csv" # Verrà creato nella root

estrai_features_batch(cartella_input, file_output_csv)