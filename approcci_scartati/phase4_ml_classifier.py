import pandas as pd
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

def addestra_valuta_modello(csv_path):
    if not os.path.exists(csv_path):
        print(f"❌ File '{csv_path}' non trovato. Esegui prima l'estrattore e annota i freeze!")
        return

    # 1. Caricamento Dati
    print(f"📥 Lettura dataset da '{csv_path}'...")
    df = pd.read_csv(csv_path)

    # Controlliamo che l'utente abbia inserito almeno un "1"
    if df['Label_Freeze'].sum() == 0:
        print("⚠️ ERRORE: Non hai etichettato nessun freeze! Apri il CSV, cerca i secondi in cui il gioco si blocca e metti '1' nella colonna 'Label_Freeze'.")
        return

    # 2. Isolamento Features (X) e Target (y)
    X = df[['AbsDiff_Perc', 'Max_Blob_Area', 'Saliency_Mean', 'Temp_Variance']]
    y = df['Label_Freeze']

    # 3. Data Splitting (80% Studio, 20% Esame)
    print("✂️ Divisione del dataset in Training Set (80%) e Test Set (20%)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 4. Inizializzazione e Addestramento
    modello_rf = RandomForestClassifier(n_estimators=300, max_depth=8, random_state=42, class_weight={0: 1.0, 1: 10.0})
    
    print("🧠 Addestramento della Random Forest in corso (Apprendimento pattern n-dimensionali)...")
    modello_rf.fit(X_train, y_train)

    # 5. Inferenza (Esame sul 20% di dati MAI visti)
    print("🎯 Valutazione del modello sul Test Set...")
    probabilita = modello_rf.predict_proba(X_test)[:, 1] # Prende le % di sicurezza per la classe "Freeze"
    soglia_sicurezza = 0.90 # Dichiara freeze solo se sei sicuro al 90% (non più al 50%)
    previsioni = (probabilita >= soglia_sicurezza).astype(int)

    # 6. Report delle Metriche per la Tesi
    print("\n========================================")
    print("📊 RISULTATI MACHINE LEARNING (Fase 4)")
    print("========================================")
    print(f"✅ Accuratezza Globale: {accuracy_score(y_test, previsioni) * 100:.2f}%\n")
    print("Report Dettagliato (Precision e Recall):")
    print(classification_report(y_test, previsioni, target_names=["Gameplay Fluido (0)", "Freeze (1)"]))

    # 7. Importanza delle Features
    importanze = modello_rf.feature_importances_
    print("========================================")
    print("🔍 IMPORTANZA DELLE FEATURES (Pesi Decisionali)")
    print("========================================")
    for feature, importanza in zip(X.columns, importanze):
        print(f"- {feature}: {importanza * 100:.2f}%")

# --- PATH RELATIVO ---
file_input_csv = "dataset_haste_features.csv" # Legge il file dalla root

addestra_valuta_modello(file_input_csv)