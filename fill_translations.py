#!/usr/bin/env python
"""
Script to fill empty Italian translations in django.po file.
"""

# Translation dictionary: English -> Italian
translations = {
    # Article Detail
    "Translated": "Tradotto",
    "Related Articles": "Articoli Correlati",
    "Back": "Indietro",
    "View Original": "Visualizza Originale",
    # Article Edit
    "Update article content and translation": "Aggiorna contenuto e traduzione dell'articolo",
    "View Article": "Visualizza Articolo",
    "Back to List": "Torna alla Lista",
    "Translation Editor": "Editor di Traduzione",
    "%(source_language)s Title": "Titolo %(source_language)s",
    "Italian Title": "Titolo Italiano",
    "%(source_language)s Content": "Contenuto %(source_language)s",
    "Italian Content": "Contenuto Italiano",
    "Save Changes": "Salva Modifiche",
    # Embedding Management
    "Embedding Management": "Gestione Embeddings",
    "Manage vector embeddings for semantic search": "Gestisci gli embeddings vettoriali per la ricerca semantica",
    "Total Articles": "Articoli Totali",
    "With Embeddings": "Con Embeddings",
    "%(embedding_percentage)s%% complete": "%(embedding_percentage)s%% completato",
    "Missing": "Mancanti",
    "With Errors": "Con Errori",
    "Embedding Models Used": "Modelli di Embedding Utilizzati",
    "Model": "Modello",
    "Articles Count": "Conteggio Articoli",
    "Percentage": "Percentuale",
    "Management Actions": "Azioni di Gestione",
    "Use these actions to manage your embeddings. Be careful as some actions cannot be undone.": "Usa queste azioni per gestire i tuoi embeddings. Attenzione, alcune azioni non possono essere annullate.",
    "This will remove all embedding data from articles. Use this before switching embedding models.": "Questo rimuoverà tutti i dati di embedding dagli articoli. Usa questo prima di cambiare modelli di embedding.",
    "Generate New Embeddings": "Genera Nuovi Embeddings",
    "Start generating embeddings for articles that don't have them using Nomic API.": "Inizia a generare embeddings per gli articoli che non li hanno usando l'API Nomic.",
    "Start Embedding Generation": "Avvia Generazione Embeddings",
    "Migration to Nomic Embeddings": "Migrazione agli Embeddings Nomic",
    "Your system is now configured to use Nomic embeddings (nomic-embed-text-v1.5) instead of VoyageAI. Remove old embeddings first, then generate new ones for better performance.": "Il tuo sistema è ora configurato per usare gli embeddings Nomic (nomic-embed-text-v1.5) invece di VoyageAI. Rimuovi prima i vecchi embeddings, poi genera quelli nuovi per prestazioni migliori.",
    "Confirm Removal": "Conferma Rimozione",
    "Yes, Remove All": "Sì, Rimuovi Tutto",
    # Index
    "Articles": "Articoli",
    "No articles found": "Nessun articolo trovato",
    "Start by adding some articles to get started.": "Inizia aggiungendo alcuni articoli per cominciare.",
    # Login
    "Login": "Accedi",
    "Welcome Back": "Bentornato",
    "Sign in to access your account": "Accedi per accedere al tuo account",
    "Invalid username or password": "Nome utente o password non validi",
    "Username": "Nome utente",
    "Enter your username": "Inserisci il tuo nome utente",
    "Password": "Password",
    "Enter your password": "Inserisci la tua password",
    "Remember me": "Ricordami",
    "Sign In": "Accedi",
    "Contact your administrator to create an account": "Contatta il tuo amministratore per creare un account",
    # Send Email
    "Send the latest translated articles to an email address": "Invia gli ultimi articoli tradotti a un indirizzo email",
    "Back to Home": "Torna alla Home",
    "Email Configuration": "Configurazione Email",
    "Sending Information": "Informazioni sull'Invio",
    "Only articles with APPROVED status will be sent": "Verranno inviati solo articoli con stato APPROVATO",
    "Articles will be sorted by translation date (most recent first)": "Gli articoli saranno ordinati per data di traduzione (più recenti per primi)",
    "After sending, the status of articles will become SENT": "Dopo l'invio, lo stato degli articoli diventerà INVIATO",
    "The email will be sent in the background and may take a few minutes": "L'email verrà inviata in background e potrebbe richiedere alcuni minuti",
    "Approved Articles": "Articoli Approvati",
    "Ready to send": "Pronti per l'invio",
    # Vector Search
    "Search articles using semantic similarity": "Cerca articoli usando la similarità semantica",
    "Enter your search query...": "Inserisci la tua ricerca...",
    "Search": "Cerca",
    "Searching...": "Ricerca in corso...",
    "No results found": "Nessun risultato trovato",
    "Try different search terms or check your spelling": "Prova termini di ricerca diversi o controlla l'ortografia",
    "Start searching": "Inizia a cercare",
    "Enter a query above to find relevant articles": "Inserisci una query sopra per trovare articoli rilevanti",
    # Scrapers
    "Scrapers": "Scrapers",
    "Manual Scrapers": "Scrapers Manuali",
    "Manually trigger news scrapers to fetch latest articles": "Attiva manualmente gli scrapers per recuperare gli ultimi articoli",
    "Scrapes latest business news from Ekapija news portal": "Recupera le ultime notizie di business dal portale Ekapija",
    "Scrapes latest business news from BiznisRS news portal": "Recupera le ultime notizie di business dal portale BiznisRS",
    "Start Scraper": "Avvia Scraper",
    "How Scrapers Work": "Come Funzionano gli Scrapers",
    "Scrapers run as background Celery tasks": "Gli scrapers vengono eseguiti come task Celery in background",
    "New articles are automatically fetched and stored": "I nuovi articoli vengono recuperati e salvati automaticamente",
    "Articles will appear in the main list after scraping completes": "Gli articoli appariranno nella lista principale dopo il completamento dello scraping",
    "Duplicate articles are automatically detected and skipped": "Gli articoli duplicati vengono rilevati e saltati automaticamente",
    "You can run multiple scrapers simultaneously": "Puoi eseguire più scrapers contemporaneamente",
    "Ekapija scraper started successfully. New articles will appear shortly.": "Scraper Ekapija avviato con successo. I nuovi articoli appariranno a breve.",
    "BiznisRS scraper started successfully. New articles will appear shortly.": "Scraper BiznisRS avviato con successo. I nuovi articoli appariranno a breve.",
    "Invalid scraper name": "Nome scraper non valido",
    "Error starting scraper: %(error)s": "Errore nell'avvio dello scraper: %(error)s",
    # Translation Service
    "Translation Service": "Servizio di Traduzione",
    "Translation": "Traduzione",
    "Automatically translate articles to Italian using AI": "Traduci automaticamente gli articoli in italiano usando l'IA",
    "AI Translation": "Traduzione IA",
    "Powered by OpenAI GPT-4": "Basato su OpenAI GPT-4",
    "This service automatically translates untranslated articles from Serbian/English to Italian using advanced AI language models.": "Questo servizio traduce automaticamente articoli non tradotti dal serbo/inglese all'italiano usando modelli linguistici IA avanzati.",
    "What gets translated:": "Cosa viene tradotto:",
    "Article titles (title_it)": "Titoli degli articoli (title_it)",
    "Article content (content_it)": "Contenuto degli articoli (content_it)",
    "Only articles without existing Italian translations": "Solo articoli senza traduzioni italiane esistenti",
    "Translation Process:": "Processo di Traduzione:",
    "Runs as a background Celery task": "Viene eseguito come task Celery in background",
    "Processes articles in batches": "Elabora gli articoli in batch",
    "Preserves original formatting and structure": "Preserva la formattazione e la struttura originale",
    "Automatically retries on failures": "Riprova automaticamente in caso di errori",
    "Start Translation": "Avvia Traduzione",
    "Best Practices": "Migliori Pratiche",
    "Run translations after scraping new articles": "Esegui le traduzioni dopo aver recuperato nuovi articoli",
    "Translated articles will be ready for validation": "Gli articoli tradotti saranno pronti per la validazione",
    "Check the main article list to see translated content": "Controlla la lista principale degli articoli per vedere i contenuti tradotti",
    "Translation quality is reviewed by AI for accuracy": "La qualità della traduzione è verificata dall'IA per accuratezza",
    "Translation service started successfully. Articles will be translated shortly.": "Servizio di traduzione avviato con successo. Gli articoli saranno tradotti a breve.",
    "Error starting translation: %(error)s": "Errore nell'avvio della traduzione: %(error)s",
    # PDF Report
    "Download PDF": "Scarica PDF",
    "Business News Report": "Report Notizie di Business",
    "Approved Articles Collection": "Raccolta Articoli Approvati",
    "Latest Articles": "Ultimi Articoli",
}


def fill_translations():
    """Read the PO file and fill in missing translations."""
    import re

    po_file = r"c:\Users\DELL\Desktop\TA\locale\it\LC_MESSAGES\django.po"

    with open(po_file, "r", encoding="utf-8") as f:
        content = f.read()

    # For each translation in our dictionary
    for english, italian in translations.items():
        # Escape special regex characters
        english_escaped = re.escape(english)

        # Pattern to find msgid with empty msgstr
        pattern = rf'(msgid "{english_escaped}"\nmsgstr ")("")'

        # Replace with Italian translation
        replacement = rf"\1{italian}\2"
        content = re.sub(pattern, replacement, content)

    # Remove fuzzy markers
    content = re.sub(r'#, fuzzy\n#\| msgid "[^"]*"\n', "", content)
    content = re.sub(r"#, fuzzy\n", "", content)

    # Write back
    with open(po_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Filled translations in {po_file}")
    print("Now run: python manage.py compilemessages --ignore=venv")


if __name__ == "__main__":
    fill_translations()
