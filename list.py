from dotenv import load_dotenv
from google import genai

# Carica la chiave API dal tuo file
load_dotenv("file.env")

# Inizializza il client
client = genai.Client()

print("Interrogazione dei server di Google in corso...\n")
print("I MODELLI DISPONIBILI PER IL TUO ACCOUNT SONO:")
print("-" * 60)

# Iteriamo direttamente sui modelli e stampiamo il loro identificativo
for model in client.models.list():
    if "gemini" in model.name:
        print(f"ID Modello da copiare: {model.name}")
        print("-" * 60)