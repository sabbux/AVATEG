import os
import json
import glob

def valuta_report_lmm(cartella_report="report_semantici"):
    file_reports = glob.glob(os.path.join(cartella_report, "*.json"))
    
    if not file_reports:
        print(f"📭 Nessun file JSON trovato nella cartella '{cartella_report}'.")
        return

    # Dizionario per raggruppare i file in base alla classificazione
    statistiche = {
        "micro_stutter": [],
        "hard_freeze": [],
        "false_positive_menu": [],
        "altri_errori": []
    }

    print(f"📊 Analisi di {len(file_reports)} report JSON in corso...\n")

    for file_path in file_reports:
        nome_file = os.path.basename(file_path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                dati = json.load(f)
            
            # Recuperiamo il fault_type (gestiamo la vecchia e la nuova struttura)
            if "diagnosi_semantica_ia" in dati:
                fault_type = dati["diagnosi_semantica_ia"]["evento_fault"]["fault_type"].lower()
            elif "diagnosi_ia" in dati:
                fault_type = dati["diagnosi_ia"]["evento_fault"]["fault_type"].lower()
            else:
                fault_type = "struttura_sconosciuta"

            # Classifichiamo il file nella categoria corretta
            if "micro_stutter" in fault_type:
                statistiche["micro_stutter"].append(nome_file)
            elif "hard_freeze" in fault_type:
                statistiche["hard_freeze"].append(nome_file)
            elif "false_positive_menu" in fault_type:
                statistiche["false_positive_menu"].append(nome_file)
            else:
                statistiche["altri_errori"].append((nome_file, fault_type))
                
        except Exception as e:
            statistiche["altri_errori"].append((nome_file, f"Errore lettura: {e}"))

    # ==========================================================
    # STAMPA DEI RISULTATI IN FORMATO LEGGIBILE
    # ==========================================================
    print("========================================================")
    print("🎯 RIEPILOGO CLASSIFICAZIONE LMM (Fase 4)")
    print("========================================================\n")
    
    for categoria, lista_file in statistiche.items():
        if categoria == "altri_errori":
            if lista_file:
                print(f"⚠️ NON CLASSIFICATI / FORMATO ERRATO ({len(lista_file)}):")
                for f, motivo in lista_file:
                    print(f"   - {f} [{motivo}]")
        else:
            print(f"🔹 {categoria.upper()} ({len(lista_file)} clip):")
            for f in lista_file:
                # Estraiamo il nome del video e il timestamp per renderlo più leggibile
                # Es: freeze_OcP-MAfImvM_351.8s_report.json -> OcP-MAfImvM a 351.8s
                nome_pulito = f.replace("freeze_", "").replace("_report.json", "")
                print(f"   - {nome_pulito}")
        print("")
        
    print("========================================================")
    
    # Calcolo dell'Accuracy
    tot_bug = len(statistiche["micro_stutter"]) + len(statistiche["hard_freeze"])
    tot_scartati = len(statistiche["false_positive_menu"])
    print(f"📈 TOTALE ALLARMI CONFERMATI (Bug Veri): {tot_bug}")
    print(f"📉 TOTALE ALLARMI SCARTATI (Falsi Positivi): {tot_scartati}")
    print("========================================================")

if __name__ == "__main__":
    valuta_report_lmm()