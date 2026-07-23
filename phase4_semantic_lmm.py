import os
import json
import time
import glob
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Configurazioni Cartelle
CARTELLA_INPUT = "anomalie_rilevate"
CARTELLA_OUTPUT = "report_semantici"

def analizza_cartella_batch():
    print(f"🚀 Avvio FASE 4: Pipeline Semantica Batch (LMM) sulla cartella: '{CARTELLA_INPUT}/'")
    
    # 1. Setup Ambiente
    os.makedirs(CARTELLA_OUTPUT, exist_ok=True)
    load_dotenv("file.env")
    client = genai.Client()

    # 2. Scansione Anomalie
    # Cerca tutti i file metadati generati dalla Golden Master
    file_metadati = glob.glob(os.path.join(CARTELLA_INPUT, "*.json"))
    
    if not file_metadati:
        print(f"📭 Nessuna anomalia trovata nella cartella '{CARTELLA_INPUT}'. Esegui prima la Golden Master.")
        return

    print(f"📦 Trovate {len(file_metadati)} anomalie da verificare. Inizio elaborazione cloud...\n")

    # 3. Loop di Elaborazione
    for meta_path in file_metadati:
        # Leggiamo cosa ha scoperto OpenCV
        with open(meta_path, "r", encoding='utf-8') as f:
            dati_cpu = json.load(f)
        
        inizio_sec = dati_cpu["inizio_sec"]
        durata_sec = dati_cpu["durata_sec"]
        video_originale = dati_cpu["video_originale"]
        
        # Deduciamo i nomi dei file
        clip_path = meta_path.replace(".json", ".mp4")
        nome_report = os.path.basename(meta_path).replace(".json", "_report.json")
        path_report_finale = os.path.join(CARTELLA_OUTPUT, nome_report)
        
        # 🛡️ RESUMABLE PIPELINE: Se il report esiste già, salta (risparmia token e tempo)
        if os.path.exists(path_report_finale):
            print(f"⏭️  [{os.path.basename(clip_path)}] Già analizzato in precedenza. Salto...")
            continue

        if not os.path.exists(clip_path):
            print(f"⚠️  Clip video mancante per '{meta_path}'. Salto...")
            continue

        print(f"🎬 Caricamento Clip: {os.path.basename(clip_path)} (Anomalia a {inizio_sec:.1f}s)")
        
        # 🛡️ IL RETRY PATTERN: Riprova lo stesso video fino a 5 volte se il server ci blocca
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

                # 5. INIEZIONE DINAMICA DEL PROMPT
                prompt = f"""
                Sei un Senior QA Engineer automatizzato. 
                Il mio sensore euristico (OpenCV) ha misurato matematicamente un blocco totale del rendering 3D esattamente dal secondo {inizio_sec} per una durata di {durata_sec} secondi.

                Il tuo compito NON è mettere in dubbio la presenza del blocco (il blocco dei frame c'è stato fisicamente in quel lasso di tempo). 
                Il tuo compito è ESCLUSIVAMENTE guardare la scena e dirmi se questo blocco è giustificabile da un evento di gioco (es. l'apertura di un menù, un caricamento voluto) oppure se è un'anomalia anormale durante il gameplay.
                
                ATTENZIONE: La morte del giocatore (hitstop/killcam) NON giustifica un blocco totale dell'aggiornamento dei frame. Se noti che il gioco scatta o si ferma durante un'azione di morte in combat, classificalo come 'micro_stutter' e NON come 'false_positive_menu'.

                DEVI RISPONDERE ESCLUSIVAMENTE CON UN OGGETTO JSON VALIDO CHE RISPETTI QUESTA STRUTTURA ESATTA:
                {{
                    "stato_pre_fault": {{
                        "environment_type": "string",
                        "player_action": "string",
                        "hud_status": "string"
                    }},
                    "evento_fault": {{
                        "fault_type": "string (scegli ESATTAMENTE tra: micro_stutter, hard_freeze, false_positive_menu)",
                        "visual_symptoms": "string (descrizione tecnica breve del perché hai scelto questa classificazione)"
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
                    model='gemini-3.5-flash',
                    contents=[video_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                
                # 7. Salvataggio su disco del Report Unificato
                report_ia = json.loads(response.text)
                report_completo = {
                    "dati_euristici_cpu": dati_cpu,
                    "diagnosi_semantica_ia": report_ia
                }
                
                with open(path_report_finale, "w", encoding='utf-8') as f:
                    json.dump(report_completo, f, indent=4)
                    
                esito = report_ia['evento_fault']['fault_type']
                print(f"   ✅ Verdetto LMM: {esito.upper()} -> Salvato in '{CARTELLA_OUTPUT}/'")
                
                # Pausa standard per non martellare il server
                time.sleep(5)
                
                # 🎯 CHIAVE DEL RETRY: Se arriviamo qui, il video è andato a buon fine. 
                # Dobbiamo interrompere il ciclo dei tentativi e passare al video successivo.
                break 
                
            except Exception as e:
                errore = str(e)
                if "429" in errore or "RESOURCE_EXHAUSTED" in errore:
                    attesa = 35 # Google chiede ~23 secondi, noi ne aspettiamo 35 per sicurezza
                    print(f"   ⚠️ Quota API superata. Riprovo lo stesso video tra {attesa}s (Tentativo {tentativo+1}/{tentativi_massimi})...")
                    time.sleep(attesa)
                else:
                    print(f"   ❌ Errore critico non recuperabile su {os.path.basename(clip_path)}: {e}")
                    break # Se è un errore diverso (es. JSON malformato), rompe il retry e va avanti
                
            finally:
                # 8. Pulizia Server ad ogni tentativo
                try:
                    client.files.delete(name=video_file.name)
                except:
                    pass

    print("\n🎉 Elaborazione Batch LMM Completata con Successo!")
    print(f"📂 Puoi consultare i report definitivi nella cartella: '{CARTELLA_OUTPUT}/'")

if __name__ == "__main__":
    analizza_cartella_batch()