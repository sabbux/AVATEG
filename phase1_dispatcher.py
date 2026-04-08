import yt_dlp
import re
import json

def esegui_fase1(input_target, modalita="ricerca", max_risultati=5):
    print(f"🌐 FASE 1: Ricerca, Smistamento e Validazione ('{input_target}')\n")
    
    # ==========================================
    # 1. DIZIONARI E REGEX (IL CERVELLO DEL DISPATCHER)
    # ==========================================
    timestamp_pattern = re.compile(r'\b(?:[0-5]?\d:)?(?:[0-5]?\d):[0-5]\d\b')
    
    # Keyword di base per identificare anomalie software
    bug_keywords = ['bug', 'glitch', 'stuck', 'crash', 'softlock', 'broken', 'issue']
    
    # Keyword per identificare montaggi e raccolte
    compilation_keywords = ['compilation', 'montage', 'collection', 'all bugs', 'every bug', 'all glitches']
    
    # Keyword NEGATIVE: scarta i video che contengono queste parole (errori umani, non software)
    fail_keywords = ['fail', 'funny', 'hilarious', 'wtf', 'troll', 'fails']
    
    # Firme di Contenuto (Pattern Regex)
    time_compilation_pattern = re.compile(r'\b\d+\s*(minutes|mins|hours|hrs)\s*of\b')
    listicle_pattern = re.compile(r'\b(?:top\s*\d+|\d+\s+(?:\w+\s+){0,3}(?:bugs|glitches|issues|softlocks))\b')
    gameplay_pattern = re.compile(r'\b(let\'s play|lets play|playthrough|walkthrough|ep\s*\d+|episode\s*\d+|part\s*\d+)\b')

    # ==========================================
    # 2. STRUTTURA DATI DI ESPORTAZIONE
    # ==========================================
    dati_esportazione = {
        "gameplays": [],    # PATH A: Necessitano di NLP sui commenti
        "compilations": [], # PATH B: Necessitano di Scene Detection visiva
        "showcases": []     # PATH C: Video interamente dedicati a un bug, da scaricare interi
    }

    ydl_opts = {
        'skip_download': True, 'getcomments': True, 'quiet': True, 'no_warnings': True,
        'extract_flat': False, 'ignoreerrors': True, 'cookiefile': 'cookies.txt', 'ignore_no_formats_error': True,
        'extractor_args': {'youtube': {'max_comments': ['200', 'all', 'all']}}
    }

    target = f"ytsearch{max_risultati}:{input_target}" if modalita == "ricerca" else input_target

    # ==========================================
    # 3. MOTORE DI RICERCA E ROUTING
    # ==========================================
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target, download=False)
            video_list = info.get('entries', [info])

            for video in video_list:
                if not video: continue
                
                titolo = video.get('title', '')
                video_id = video.get('id')
                url = video.get('webpage_url', f"https://www.youtube.com/watch?v={video_id}")
                titolo_lower = titolo.lower()
                
                print(f"-> Analizzo: {titolo}")

                # Check delle condizioni
                is_fail = any(kw in titolo_lower for kw in fail_keywords)
                is_compilation = any(kw in titolo_lower for kw in compilation_keywords)
                is_time_comp = bool(time_compilation_pattern.search(titolo_lower))
                is_listicle = bool(listicle_pattern.search(titolo_lower))
                is_let_play = bool(gameplay_pattern.search(titolo_lower))
                has_bug_keyword = any(kw in titolo_lower for kw in bug_keywords)
                
                # NUOVO CONTROLLO: Estrae il limite di età (se non esiste, assume 0)
                age_limit = video.get('age_limit', 0)
                is_restricted = (age_limit is not None and age_limit >= 18)

                # --- ALBERO DECISIONALE DI SMISTAMENTO ---
                
                # 1. FILTRO ANTI-BLOCCO YOUTUBE (+18)
                if is_restricted:
                    print("   [SCARTATO] Rilevato come +18/Age-Restricted. Scartato per evitare blocchi crittografici (PO Token).")
                    continue
                
                # 2. FILTRO ERRORI UMANI
                elif is_fail:
                    print("   [SCARTATO] Rilevato come Fail/Umoristico (Errore umano, non del software).")
                    continue
                    
                # 3. PATH B: COMPILATION
                elif is_compilation or is_time_comp or is_listicle:
                    print("   [Smistato in PATH B] Rilevato come Compilation / Listicle.")
                    dati_esportazione["compilations"].append({
                        "video_id": video_id, "titolo": titolo, "url": url
                    })
                    
                # 4. PATH C: SHOWCASE
                elif has_bug_keyword and not is_let_play:
                    print("   [Smistato in PATH C] Rilevato come Showcase/Tutorial dedicato.")
                    dati_esportazione["showcases"].append({
                        "video_id": video_id, "titolo": titolo, "url": url
                    })
                    
                # 5. PATH A: GAMEPLAY STANDARD
                else:
                    print("   [Smistato in PATH A] Rilevato come Gameplay o video standard. Cerco timestamp...")
                    commenti = video.get('comments', [])
                    timestamps_trovati = []
                    
                    for commento in commenti:
                        testo = commento.get('text', '').lower()
                        if any(kw in testo for kw in bug_keywords):
                            timestamps_trovati.extend(timestamp_pattern.findall(testo))
                    
                    if timestamps_trovati:
                        print(f"   [+] Trovati {len(timestamps_trovati)} timestamp validi.")
                        dati_esportazione["gameplays"].append({
                            "video_id": video_id, "titolo": titolo, "url": url,
                            "timestamps_grezzi": timestamps_trovati
                        })
                    else:
                        print("   [-] Nessun timestamp rilevante. Scartato in sicurezza.")

    except Exception as e:
         print(f"Errore durante l'estrazione: {e}")

    # ==========================================
    # 4. SALVATAGGIO DEL DATABASE PONTE
    # ==========================================
    with open('risultati_fase1.json', 'w', encoding='utf-8') as f:
        json.dump(dati_esportazione, f, indent=4)
    
    print("\n✅ Fase 1 completata con successo.")
    print("Statistiche finali salvate in 'risultati_fase1.json':")
    print(f" - Path A (Gameplay da ritagliare): {len(dati_esportazione['gameplays'])}")
    print(f" - Path B (Compilation da analizzare visivamente): {len(dati_esportazione['compilations'])}")
    print(f" - Path C (Showcase da scaricare interi): {len(dati_esportazione['showcases'])}")

# ==========================================
# PANNELLO DI CONTROLLO
# ==========================================
if __name__ == "__main__":
    QUERY_DI_TEST = "Fallout freeze bug"
    esegui_fase1(input_target=QUERY_DI_TEST, modalita="ricerca", max_risultati=5)