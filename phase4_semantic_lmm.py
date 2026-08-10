import os
import json
import time
import glob
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Configurazioni Cartelle
CARTELLA_INPUT = "clip_da_analizzare" # <- Cartella root dove i 3 moduli yt-dlp e OpenCV salvano le clip
CARTELLA_OUTPUT = "report_semantici_generali"

def analizza_cartella_batch():
    print(f"🚀 Avvio FASE 4: Pipeline Semantica Multi-Sorgente (LMM) in '{CARTELLA_INPUT}'")
    
    # 1. Setup Ambiente
    os.makedirs(CARTELLA_OUTPUT, exist_ok=True)
    load_dotenv("file.env")
    client = genai.Client()

    # 2. Scansione Anomalie (Ricerca Ricorsiva in tutte le sottocartelle)
    file_metadati = glob.glob(os.path.join(CARTELLA_INPUT, "**", "*.json"), recursive=True)
    
    if not file_metadati:
        print(f"📭 Nessuna clip trovata. Esegui prima i moduli di clipping (Fase 2).")
        return

    print(f"📦 Trovate {len(file_metadati)} clip da analizzare. Inizio elaborazione cloud...\n")

    # 3. Loop di Elaborazione
    for meta_path in file_metadati:
        with open(meta_path, "r", encoding='utf-8') as f:
            dati_input = json.load(f)
        
        # Recuperiamo la radice dei dati (funziona sia per CPU locale che per moduli yt-dlp)
        dati_radice = dati_input.get("dati_euristici_cpu", {})
        
        inizio_sec = dati_radice.get("inizio_sec", 0.0)
        tipo_sospetto = dati_radice.get("tipo_anomalia_sospetta", "sconosciuto")
        
        # Deduciamo i file
        clip_path = meta_path.replace(".json", ".mp4")
        nome_report = os.path.basename(meta_path).replace(".json", "_report.json")
        path_report_finale = os.path.join(CARTELLA_OUTPUT, nome_report)
        
        # 🛡️ RESUMABLE PIPELINE
        if os.path.exists(path_report_finale):
            print(f"⏭️  [{os.path.basename(clip_path)}] Già analizzato. Salto...")
            continue

        if not os.path.exists(clip_path):
            print(f"⚠️  Clip video mancante per '{meta_path}'. Salto...")
            continue

        print(f"🎬 Analizzo: {os.path.basename(clip_path)} (Fonte: {tipo_sospetto})")
        
        # 🛡️ IL RETRY PATTERN
        tentativi_massimi = 5
        for tentativo in range(tentativi_massimi):
            try:
                # 4. Upload sicuro sui server di Google
                video_file = client.files.upload(file=clip_path)
                
                while True:
                    video_info = client.files.get(name=video_file.name)
                    if video_info.state == "ACTIVE":
                        break
                    elif video_info.state == "FAILED":
                        raise Exception("Elaborazione video fallita lato server.")
                    time.sleep(2)

                # 5. INIEZIONE DINAMICA DEL PROMPT (AGGIORNATA PER GENERAL-PURPOSE)
                prompt = f"""
                Sei un Senior QA Engineer automatizzato per videogiochi. 
                Questa clip video ti è stata sottoposta perché un modulo precedente della nostra pipeline ha etichettato il video con questo sospetto: '{tipo_sospetto}'.
                Il punto di interesse o di inizio teorico è al secondo {inizio_sec}.

                Il tuo compito è analizzare la scena video nella sua interezza e diagnosticare COSA sta succedendo a schermo. 
                Poiché questa clip potrebbe provenire da fonti diverse (es. analisi pixel OpenCV, commenti degli utenti, compilations di bug), NON limitarti a cercare solo cali di frame. 
                
                Devi cercare e classificare qualsiasi tipo di anomalia visibile, tra cui:
                - Anomalie prestazionali (micro_stutter, hard_freeze)
                - Anomalie fisiche/motore di gioco (clipping, compenetrazione poligonale, caduta fuori mappa)
                - Anomalie logiche (softlock, UI rotta, comportamenti IA assurdi)
                - Eventi normali scambiati per bug (false_positive_menu, death_cam, normal_gameplay)

                DEVI RISPONDERE ESCLUSIVAMENTE CON UN OGGETTO JSON VALIDO CHE RISPETTI QUESTA STRUTTURA:
                {{
                    "stato_pre_fault": {{
                        "environment_type": "string",
                        "player_action": "string",
                        "hud_status": "string"
                    }},
                    "evento_fault": {{
                        "fault_category": "string (scegli ESATTAMENTE tra: performance, physics, logic, false_positive)",
                        "fault_type": "string (es: micro_stutter, hard_freeze, clipping, softlock, false_positive_menu, normal_gameplay)",
                        "visual_symptoms": "string (descrizione tecnica breve di cosa si vede a schermo e perché hai scelto questa classificazione)"
                    }},
                    "stato_post_fault": {{
                        "environment_type": "string",
                        "player_action": "string",
                        "hud_status": "string"
                    }}
                }}
                """

                # 6. Chiamata al modello IA
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[video_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                
                # 7. Salvataggio su disco del Report Unificato
                report_ia = json.loads(response.text)
                report_completo = {
                    "dati_euristici_cpu": dati_radice,
                    "diagnosi_semantica_ia": report_ia
                }
                
                with open(path_report_finale, "w", encoding='utf-8') as f:
                    json.dump(report_completo, f, indent=4)
                    
                esito = report_ia['evento_fault']['fault_type']
                print(f"   ✅ Verdetto LMM: {esito.upper()} -> Salvato!")
                
                time.sleep(5)
                break 
                
            except Exception as e:
                errore = str(e)
                # Intercetta sia l'errore 429 (Quota) che l'errore 503 (Server Saturo)
                if "429" in errore or "RESOURCE_EXHAUSTED" in errore or "503" in errore or "UNAVAILABLE" in errore:
                    
                    # Backoff Esponenziale: Aumentiamo l'attesa ad ogni fallimento
                    attesa_base = 35 
                    attesa = attesa_base * (tentativo + 1) # Es: 35s -> 70s -> 105s
                    
                    if "503" in errore:
                        print(f"   ⏳ Server Google saturi (Errore 503). Pausa lunga di {attesa}s (Tentativo {tentativo+1}/{tentativi_massimi})...")
                    else:
                        print(f"   ⚠️ Quota API superata (Errore 429). Riprovo tra {attesa}s (Tentativo {tentativo+1}/{tentativi_massimi})...")
                        
                    time.sleep(attesa)
                else:
                    print(f"   ❌ Errore critico su {os.path.basename(clip_path)}: {e}")
                    break

    print("\n🎉 Elaborazione Batch LMM Completata con Successo!")
    print(f"📂 Puoi consultare i report definitivi nella cartella: '{CARTELLA_OUTPUT}/'")

if __name__ == "__main__":
    analizza_cartella_batch()