import pandas as pd
import yt_dlp
import os

# --- CONFIGURAZIONE ASSOLUTA ---
# Trova la cartella esatta in cui si trova QUESTO file Python
CARTELLA_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# Unisce la cartella dello script al nome del file (funzionerà ovunque!)
FILE_CSV = os.path.join(CARTELLA_SCRIPT, 'videos.csv')
CARTELLA_OUTPUT = os.path.join(CARTELLA_SCRIPT, 'dataset_haste')
NOME_COLONNA_URL = 'link_youtube'

def scarica_video_haste():
    print(f"📥 Inizializzazione Download dal dataset: {FILE_CSV}")
    
    # Crea la cartella di destinazione se non esiste
    os.makedirs(CARTELLA_OUTPUT, exist_ok=True)
    
    # 1. Leggi il CSV
    try:
        df = pd.read_csv(FILE_CSV)
        # Se il file usa il punto e virgola invece della virgola, decommenta la riga sotto e cancella quella sopra:
        # df = pd.read_csv(FILE_CSV, sep=';')
    except FileNotFoundError:
        print(f"❌ Errore: Il file {FILE_CSV} non è stato trovato nella cartella corrente.")
        return

    # Controlla che la colonna esista
    if NOME_COLONNA_URL not in df.columns:
        print(f"❌ Errore: La colonna '{NOME_COLONNA_URL}' non esiste. Le colonne disponibili sono: {list(df.columns)}")
        print("Modifica la variabile NOME_COLONNA_URL nello script in base al nome corretto.")
        return

    urls = df[NOME_COLONNA_URL].dropna().tolist()
    print(f"Trovati {len(urls)} video nel CSV. Inizio il processo...")

    # 2. Configurazione di yt-dlp
    ydl_opts = {
        # Scarica il miglior video MP4 + audio M4A e uniscili. Se fallisce, prendi il miglior MP4 singolo.
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        
        # ⚠️ CRUCIALE: Salva il file chiamandolo ESATTAMENTE con il suo ID YouTube (es. dQw4w9WgXcQ.mp4)
        # Questo ti salverà la vita quando dovrai incrociare i file con oracle.csv
        'outtmpl': os.path.join(CARTELLA_OUTPUT, '%(id)s.%(ext)s'),
        
        'ignoreerrors': True, # Se un video è stato cancellato, passa al successivo senza crashare
        'quiet': False,       # Mostra la barra di avanzamento
        'no_warnings': True,
    }

    video_scaricati = 0
    video_falliti = 0

    # 3. Ciclo di download
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, url in enumerate(urls):
            print(f"\n⏳ Elaborazione {i+1}/{len(urls)}: {url}")
            
            # Se nel CSV ci sono solo gli ID e non l'URL completo, ricostruiamolo:
            if not url.startswith('http'):
                url = f"https://www.youtube.com/watch?v={url}"

            try:
                # Estrae le info e scarica
                info_dict = ydl.extract_info(url, download=True)
                if info_dict is not None:
                    video_scaricati += 1
                else:
                    video_falliti += 1
            except Exception as e:
                print(f"[!] Impossibile scaricare {url}: {e}")
                video_falliti += 1

    # 4. Report Finale
    print("\n" + "="*40)
    print("✅ PROCESSO TERMINATO")
    print(f"📁 Video salvati in: '{CARTELLA_OUTPUT}/'")
    print(f"🟢 Scaricati con successo: {video_scaricati}")
    print(f"🔴 Falliti/Rimossi da YouTube: {video_falliti}")
    print("="*40)

if __name__ == "__main__":
    scarica_video_haste()